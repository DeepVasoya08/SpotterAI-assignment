from datetime import timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from services.corridor_forecast import FORECAST_HOURS, CorridorForecaster
from tests.fakes import FakeWeather
from trips import providers

URL = reverse("corridor-forecast")


@pytest.fixture(autouse=True)
def fake_weather(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(providers, "corridor_forecaster", lambda: CorridorForecaster(FakeWeather()))


def payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "paths": [[{"lat": 40, "lon": -100}, {"lat": 40, "lon": -98}]],
        "departure_time": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_weight_lb": 40_000,
    }
    body.update(overrides)
    return body


def test_returns_hourly_cells() -> None:
    response = APIClient().post(URL, payload(), format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["hours"] == FORECAST_HOURS + 1
    assert body["step_degrees"] > 0
    cell = body["cells"][0]
    assert set(cell) == {"lat", "lon", "risk", "wind_gust_mph", "rain_in_per_hr", "snow_in_per_hr"}
    assert len(cell["risk"]) == FORECAST_HOURS + 1
    assert cell["risk"][0] == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"paths": []},
        {"paths": [[{"lat": 40, "lon": -100}]]},
        {"paths": [[{"lat": 40, "lon": -100}, {"lat": 40, "lon": -98}]] * 4},
        {"departure_time": (timezone.now() - timedelta(days=1)).isoformat()},
        {"load_weight_lb": 100_000},
    ],
)
def test_rejects_invalid_input(overrides: dict[str, Any]) -> None:
    response = APIClient().post(URL, payload(**overrides), format="json")

    assert response.status_code == 400
