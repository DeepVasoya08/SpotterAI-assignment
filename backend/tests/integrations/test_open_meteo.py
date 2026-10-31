from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx

from domain.geo import GeoPoint
from integrations.errors import ProviderError
from integrations.open_meteo import BASE_URL, LOCATIONS_PER_REQUEST, OpenMeteoClient

START = datetime(2026, 11, 1, 12, 40, tzinfo=UTC)
END = datetime(2026, 11, 1, 13, 10, tzinfo=UTC)


def location(wind: list[float | None], rain: list[float], showers: list[float]) -> dict[str, Any]:
    hours = len(wind)
    return {
        "hourly": {
            "time": [f"2026-11-01T{12 + h:02d}:00" for h in range(hours)],
            "wind_speed_10m": wind,
            "wind_gusts_10m": [w if w is None else w + 5 for w in wind],
            "rain": rain,
            "showers": showers,
            "snowfall": [0.0] * hours,
        }
    }


@pytest.fixture
def client() -> OpenMeteoClient:
    return OpenMeteoClient(httpx.Client())


@respx.mock
def test_requests_whole_hours_in_truck_units(client: OpenMeteoClient) -> None:
    route = respx.get(BASE_URL).respond(json=location([10, 12, 14], [0, 0, 0], [0, 0, 0]))

    client.hourly_forecasts([GeoPoint(40, -100)], START, END)

    params = route.calls.last.request.url.params
    assert params["start_hour"] == "2026-11-01T12:00"
    assert params["end_hour"] == "2026-11-01T14:00"
    assert params["wind_speed_unit"] == "mph"
    assert params["precipitation_unit"] == "inch"


@respx.mock
def test_parses_each_location_in_order(client: OpenMeteoClient) -> None:
    respx.get(BASE_URL).respond(
        json=[
            location([10, 11], [0.1, 0.2], [0.05, 0.0]),
            location([30, 31], [0.0, 0.0], [0.0, 0.0]),
        ]
    )
    points = [GeoPoint(40, -100), GeoPoint(41, -101)]

    forecasts = client.hourly_forecasts(points, START, END)

    assert [f.point for f in forecasts] == points
    assert forecasts[0].start == datetime(2026, 11, 1, 12, tzinfo=UTC)
    assert forecasts[0].rain_in == pytest.approx((0.15, 0.2))
    assert forecasts[1].wind_gust_mph == (35, 36)


@respx.mock
def test_missing_values_are_treated_as_calm(client: OpenMeteoClient) -> None:
    respx.get(BASE_URL).respond(json=location([None, 12], [0, 0], [0, 0]))

    (forecast,) = client.hourly_forecasts([GeoPoint(40, -100)], START, END)

    assert forecast.wind_speed_mph == (0.0, 12.0)


@respx.mock
def test_splits_many_locations_into_chunks(client: OpenMeteoClient) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        count = len(request.url.params["latitude"].split(","))
        return httpx.Response(200, json=[location([5], [0], [0]) for _ in range(count)])

    route = respx.get(BASE_URL).mock(side_effect=respond)
    points = [GeoPoint(30 + i / 100, -100) for i in range(LOCATIONS_PER_REQUEST * 2 + 1)]

    forecasts = client.hourly_forecasts(points, START, END)

    assert route.call_count == 3
    assert [f.point for f in forecasts] == points


@respx.mock
def test_http_error_raises_provider_error(client: OpenMeteoClient) -> None:
    respx.get(BASE_URL).respond(400, json={"error": True, "reason": "Latitude out of range"})

    with pytest.raises(ProviderError, match="Latitude out of range"):
        client.hourly_forecasts([GeoPoint(40, -100)], START, END)


@respx.mock
def test_mismatched_location_count_raises_provider_error(client: OpenMeteoClient) -> None:
    respx.get(BASE_URL).respond(json=[location([1], [0], [0])])

    with pytest.raises(ProviderError, match="number of locations"):
        client.hourly_forecasts([GeoPoint(40, -100), GeoPoint(41, -100)], START, END)


@respx.mock
def test_malformed_payload_raises_provider_error(client: OpenMeteoClient) -> None:
    respx.get(BASE_URL).respond(json={"hourly": {"time": []}})

    with pytest.raises(ProviderError, match="malformed"):
        client.hourly_forecasts([GeoPoint(40, -100)], START, END)
