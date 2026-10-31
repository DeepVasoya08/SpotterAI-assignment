from datetime import timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from domain.geo import GeoPoint
from integrations.errors import ProviderError
from integrations.routing import Place
from services.trip_planner import TripPlanner
from tests.fakes import FakeRouting, FakeWeather, east_west_route
from trips import providers


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def routing(monkeypatch: pytest.MonkeyPatch) -> FakeRouting:
    fake = FakeRouting(primary=[east_west_route(lat=40), east_west_route(lat=41)])
    monkeypatch.setattr(providers, "here_client", lambda: fake)
    monkeypatch.setattr(providers, "trip_planner", lambda: TripPlanner(fake, FakeWeather()))
    return fake


def trip_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "origin": {"lat": 40, "lon": -100},
        "destination": {"lat": 40, "lon": -98},
        "departure_time": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_weight_lb": 35_000,
        "sampling_interval_miles": 25,
    }
    payload.update(overrides)
    return payload


class TestTripPlan:
    url = reverse("trip-plan")

    def test_returns_routes_checkpoints_and_recommendation(
        self, api: APIClient, routing: FakeRouting
    ) -> None:
        response = api.post(self.url, trip_payload(), format="json")

        assert response.status_code == 200
        body = response.json()
        assert body["recommendation"]["route_id"] in {"route-1", "route-2"}
        assert len(body["routes"]) == 2

        route = body["routes"][0]
        assert route["geometry"][0] == [-100.0, 40.0]
        assert route["geometry"][-1] == [-98.0, 40.0]
        assert set(route["summary"]["miles_by_level"]) == {
            "low",
            "moderate",
            "high",
            "severe",
            "no_travel",
        }
        checkpoint = route["checkpoints"][1]
        assert checkpoint["distance_miles"] == 25
        assert checkpoint["risk"]["level"] == "low"
        assert set(checkpoint["weather"]) == {
            "wind_speed_mph",
            "wind_gust_mph",
            "rain_in_per_hr",
            "snow_in_per_hr",
        }

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"sampling_interval_miles": 15}, "sampling_interval_miles"),
            ({"load_weight_lb": 0}, "load_weight_lb"),
            ({"load_weight_lb": 90_000}, "load_weight_lb"),
            ({"origin": {"lat": 95, "lon": 0}}, "origin"),
            ({"departure_time": "not-a-date"}, "departure_time"),
        ],
    )
    def test_rejects_invalid_input(
        self, api: APIClient, routing: FakeRouting, overrides: dict[str, Any], field: str
    ) -> None:
        response = api.post(self.url, trip_payload(**overrides), format="json")

        assert response.status_code == 400
        assert field in response.json()

    @pytest.mark.parametrize(
        ("offset", "message"),
        [(timedelta(hours=-2), "past"), (timedelta(days=8), "7 days")],
    )
    def test_rejects_departure_outside_forecast_window(
        self, api: APIClient, routing: FakeRouting, offset: timedelta, message: str
    ) -> None:
        departure = (timezone.now() + offset).isoformat()

        response = api.post(self.url, trip_payload(departure_time=departure), format="json")

        assert response.status_code == 400
        assert message in response.json()["departure_time"][0]

    def test_rejects_identical_origin_and_destination(
        self, api: APIClient, routing: FakeRouting
    ) -> None:
        point = {"lat": 40, "lon": -100}

        response = api.post(self.url, trip_payload(destination=point), format="json")

        assert response.status_code == 400

    def test_no_route_is_unprocessable(self, api: APIClient, routing: FakeRouting) -> None:
        routing.primary = []

        response = api.post(self.url, trip_payload(), format="json")

        assert response.status_code == 422
        assert "No truck route" in response.json()["detail"]

    def test_provider_failure_is_bad_gateway(
        self, api: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FailingPlanner:
            def plan(self, request: object) -> None:
                raise ProviderError("HERE", "HTTP 503")

        monkeypatch.setattr(providers, "trip_planner", FailingPlanner)

        response = api.post(self.url, trip_payload(), format="json")

        assert response.status_code == 502
        assert response.json() == {
            "detail": "HERE is unavailable right now. Please try again shortly."
        }


class TestPlaceSearch:
    url = reverse("place-search")

    def test_returns_suggestions(self, api: APIClient, routing: FakeRouting) -> None:
        routing.places = [Place("here:1", "Denver, CO", GeoPoint(39.74, -104.99))]

        response = api.get(self.url, {"q": "Denver"})

        assert response.status_code == 200
        assert response.json() == {
            "results": [{"id": "here:1", "label": "Denver, CO", "lat": 39.74, "lon": -104.99}]
        }

    def test_caches_repeated_queries(self, api: APIClient, routing: FakeRouting) -> None:
        api.get(self.url, {"q": "Denver"})
        api.get(self.url, {"q": "denver"})

        assert routing.place_queries == ["Denver"]

    def test_requires_three_characters(self, api: APIClient, routing: FakeRouting) -> None:
        response = api.get(self.url, {"q": "De"})

        assert response.status_code == 400
