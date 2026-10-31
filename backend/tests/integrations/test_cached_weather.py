from datetime import UTC, datetime, timedelta

from django.core.cache.backends.locmem import LocMemCache

from domain.geo import GeoPoint
from integrations.cached_weather import CachedWeatherProvider
from tests.fakes import FakeWeather

START = datetime(2026, 11, 2, 8, tzinfo=UTC)
END = START + timedelta(hours=48)


def provider() -> tuple[CachedWeatherProvider, FakeWeather]:
    fake = FakeWeather()
    # LocMemCache instances with the same name share storage, so start from empty.
    cache = LocMemCache("test-forecasts", {})
    cache.clear()
    return CachedWeatherProvider(fake, cache), fake


def test_fetches_only_uncached_points() -> None:
    cached, fake = provider()
    a, b, c = GeoPoint(40, -100), GeoPoint(40.2, -100), GeoPoint(40.4, -100)

    cached.hourly_forecasts([a, b], START, END)
    forecasts = cached.hourly_forecasts([b, c, a], START, END)

    assert fake.requested_points == [a, b, c]
    assert [forecast.point for forecast in forecasts] == [b, c, a]


def test_different_time_window_is_a_cache_miss() -> None:
    cached, fake = provider()
    point = GeoPoint(40, -100)

    cached.hourly_forecasts([point], START, END)
    cached.hourly_forecasts([point], START + timedelta(hours=1), END + timedelta(hours=1))

    assert fake.requested_points == [point, point]
