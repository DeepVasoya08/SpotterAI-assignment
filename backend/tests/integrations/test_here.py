from datetime import UTC, datetime
from typing import Any

import flexpolyline
import httpx
import pytest
import respx

from domain.geo import GeoPoint
from integrations.errors import ProviderError
from integrations.here import AUTOSUGGEST_URL, ROUTES_URL, HereClient

API_KEY = "test-key"
DEPARTURE = datetime(2026, 11, 1, 14, tzinfo=UTC)
ORIGIN = GeoPoint(41.8781, -87.6298)
DESTINATION = GeoPoint(39.7392, -104.9903)


def section(
    points: list[tuple[float, float]],
    duration_s: int,
    length_m: int,
    spans: list[dict[str, int]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "polyline": flexpolyline.encode(points),
        "summary": {"duration": duration_s, "length": length_m},
    }
    if spans is not None:
        payload["spans"] = spans
    return payload


@pytest.fixture
def client() -> HereClient:
    return HereClient(API_KEY, httpx.Client())


def plan(client: HereClient, via: tuple[GeoPoint, ...] = ()) -> Any:
    return client.truck_routes(ORIGIN, DESTINATION, DEPARTURE, gross_weight_lb=40_000, via=via)


class TestTruckRoutes:
    @respx.mock
    def test_requests_truck_routes_with_weight_in_kilograms(self, client: HereClient) -> None:
        route = respx.get(ROUTES_URL).respond(json={"routes": []})

        plan(client)

        params = route.calls.last.request.url.params
        assert params["transportMode"] == "truck"
        assert params["vehicle[grossWeight]"] == "18144"
        assert params["departureTime"] == "2026-11-01T14:00:00+00:00"
        assert params["alternatives"] == "2"
        assert params["apiKey"] == API_KEY

    @respx.mock
    def test_via_points_replace_alternatives(self, client: HereClient) -> None:
        route = respx.get(ROUTES_URL).respond(json={"routes": []})

        plan(client, via=(GeoPoint(40, -95),))

        params = route.calls.last.request.url.params
        assert params.get_list("via") == ["40.000000,-95.000000"]
        assert "alternatives" not in params

    @respx.mock
    def test_spreads_span_durations_across_vertices_by_distance(self, client: HereClient) -> None:
        # Two equal-length segments in the first span (600 s), one in the second (900 s).
        points = [(40.0, -100.0), (40.0, -99.9), (40.0, -99.8), (40.0, -99.7)]
        spans = [{"offset": 0, "duration": 600}, {"offset": 2, "duration": 900}]
        respx.get(ROUTES_URL).respond(
            json={"routes": [{"sections": [section(points, 1500, 25_750, spans)]}]}
        )

        (option,) = plan(client)

        assert option.path.elapsed_s == pytest.approx((0, 300, 600, 1500))
        assert option.duration_s == 1500
        assert option.distance_miles == pytest.approx(16.0, abs=0.01)

    @respx.mock
    def test_without_spans_uses_section_duration(self, client: HereClient) -> None:
        points = [(40.0, -100.0), (40.0, -99.9), (40.0, -99.8)]
        respx.get(ROUTES_URL).respond(
            json={"routes": [{"sections": [section(points, 1000, 17_000)]}]}
        )

        (option,) = plan(client)

        assert option.path.elapsed_s == pytest.approx((0, 500, 1000))

    @respx.mock
    def test_joins_sections_of_a_via_route(self, client: HereClient) -> None:
        first = section([(40.0, -100.0), (40.0, -99.9)], 600, 8_500)
        second = section([(40.0, -99.9), (40.0, -99.8)], 400, 8_500)
        respx.get(ROUTES_URL).respond(json={"routes": [{"sections": [first, second]}]})

        (option,) = plan(client, via=(GeoPoint(40, -99.9),))

        assert len(option.path.points) == 3
        assert option.path.elapsed_s == pytest.approx((0, 600, 1000))
        assert option.duration_s == 1000

    @respx.mock
    def test_returns_every_alternative(self, client: HereClient) -> None:
        points = [(40.0, -100.0), (40.0, -99.9)]
        respx.get(ROUTES_URL).respond(
            json={"routes": [{"sections": [section(points, 600, 8_500)]} for _ in range(3)]}
        )

        assert len(plan(client)) == 3

    @respx.mock
    def test_error_response_raises_provider_error_without_leaking_key(
        self, client: HereClient
    ) -> None:
        respx.get(ROUTES_URL).respond(401, json={"title": "Unauthorized"})

        with pytest.raises(ProviderError, match="HTTP 401: Unauthorized") as error:
            plan(client)

        assert API_KEY not in str(error.value)

    @respx.mock
    def test_malformed_route_raises_provider_error(self, client: HereClient) -> None:
        respx.get(ROUTES_URL).respond(json={"routes": [{"sections": [{}]}]})

        with pytest.raises(ProviderError, match="malformed"):
            plan(client)

    @respx.mock
    def test_network_failure_raises_provider_error(self, client: HereClient) -> None:
        respx.get(ROUTES_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

        with pytest.raises(ProviderError, match="request failed"):
            plan(client)


class TestSearchPlaces:
    @respx.mock
    def test_returns_places_with_positions(self, client: HereClient) -> None:
        route = respx.get(AUTOSUGGEST_URL).respond(
            json={
                "items": [
                    {
                        "id": "here:1",
                        "title": "Denver",
                        "address": {"label": "Denver, CO, United States"},
                        "position": {"lat": 39.74, "lng": -104.99},
                    },
                    {"id": "here:2", "title": "Denver restaurants"},
                    {"id": "here:3", "title": "Dallas", "position": {"lat": 32.78, "lng": -96.8}},
                ]
            }
        )

        places = client.search_places("Den", limit=5)

        assert [(p.id, p.label, p.point) for p in places] == [
            ("here:1", "Denver, CO, United States", GeoPoint(39.74, -104.99)),
            ("here:3", "Dallas", GeoPoint(32.78, -96.8)),
        ]
        params = route.calls.last.request.url.params
        assert params["in"] == "countryCode:USA"
        assert params["limit"] == "5"

    @respx.mock
    def test_error_raises_provider_error(self, client: HereClient) -> None:
        respx.get(AUTOSUGGEST_URL).respond(429, json={"title": "Too Many Requests"})

        with pytest.raises(ProviderError, match="429"):
            client.search_places("Den", limit=5)

    @respx.mock
    def test_malformed_item_raises_provider_error(self, client: HereClient) -> None:
        respx.get(AUTOSUGGEST_URL).respond(json={"items": [{"position": {"lat": 1}}]})

        with pytest.raises(ProviderError, match="malformed"):
            client.search_places("Den", limit=5)
