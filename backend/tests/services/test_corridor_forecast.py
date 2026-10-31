from domain.geo import GeoPoint
from domain.risk import RiskLevel
from services.corridor_forecast import FORECAST_HOURS, CorridorForecaster
from tests.fakes import DEPARTURE, FakeWeather

PATH = [GeoPoint(40, -100), GeoPoint(40, -98)]


def test_returns_hourly_series_from_departure() -> None:
    forecast = CorridorForecaster(FakeWeather()).forecast([PATH], DEPARTURE, 40_000)

    assert forecast.start == DEPARTURE
    assert forecast.cells
    assert all(len(cell.levels) == FORECAST_HOURS + 1 for cell in forecast.cells)


def test_risk_changes_over_time_and_uses_load_weight() -> None:
    # Gusts of 40 mph arrive six hours after departure.
    weather = FakeWeather(weather=lambda point, hour: (40, 0, 0) if hour >= 6 else (5, 0, 0))

    light = CorridorForecaster(weather).forecast([PATH], DEPARTURE, 20_000)
    heavy = CorridorForecaster(weather).forecast([PATH], DEPARTURE, 45_000)

    assert light.cells[0].levels[0] is RiskLevel.LOW
    assert light.cells[0].levels[6] is RiskLevel.HIGH
    assert heavy.cells[0].levels[6] is RiskLevel.SEVERE


def test_fetches_one_forecast_per_cell() -> None:
    weather = FakeWeather()

    forecast = CorridorForecaster(weather).forecast([PATH, PATH], DEPARTURE, 40_000)

    assert len(weather.requested_points) == len(forecast.cells)
