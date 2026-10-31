from datetime import UTC, datetime, timedelta

import pytest

from domain.forecast import ForecastUnavailableError, HourlyForecast
from domain.geo import GeoPoint

START = datetime(2026, 11, 1, 12, tzinfo=UTC)


def forecast() -> HourlyForecast:
    return HourlyForecast(
        point=GeoPoint(40, -100),
        start=START,
        wind_speed_mph=(10, 20, 30),
        wind_gust_mph=(15, 25, 35),
        rain_in=(0.0, 0.1, 0.2),
        snow_in=(0.0, 0.5, 1.0),
    )


def test_exact_hour_uses_that_hour() -> None:
    conditions = forecast().conditions_at(START + timedelta(hours=1))

    assert conditions.wind_speed_mph == 20
    assert conditions.rain_in_per_hr == 0.1


def test_wind_uses_nearest_hour() -> None:
    conditions = forecast().conditions_at(START + timedelta(minutes=100))

    assert conditions.wind_speed_mph == 30
    assert conditions.wind_gust_mph == 35


def test_precipitation_uses_hour_containing_the_moment() -> None:
    conditions = forecast().conditions_at(START + timedelta(minutes=20))

    assert conditions.rain_in_per_hr == 0.1
    assert conditions.snow_in_per_hr == 0.5
    assert conditions.wind_speed_mph == 10


@pytest.mark.parametrize(
    "moment",
    [START - timedelta(hours=1), START + timedelta(hours=2, minutes=1)],
)
def test_moment_outside_range_is_rejected(moment: datetime) -> None:
    with pytest.raises(ForecastUnavailableError):
        forecast().conditions_at(moment)


def test_requires_timezone_aware_start() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HourlyForecast(GeoPoint(0, 0), datetime(2026, 1, 1), (1,), (1,), (0,), (0,))


def test_requires_equal_series_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        HourlyForecast(GeoPoint(0, 0), START, (1, 2), (1,), (0,), (0,))
