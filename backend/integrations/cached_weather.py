"""Per-location forecast cache in front of a weather provider.

Corridor cells sit on a fixed lattice, so reopening a plan or re-planning the same trip
reuses forecasts instead of spending the provider's daily request quota again.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from django.core.cache.backends.base import BaseCache

from domain.forecast import HourlyForecast
from domain.geo import GeoPoint

CACHE_SECONDS = 30 * 60
HOUR_KEY_FORMAT = "%Y%m%d%H"


class WeatherProvider(Protocol):
    def hourly_forecasts(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlyForecast]: ...


class CachedWeatherProvider:
    def __init__(self, provider: WeatherProvider, cache: BaseCache) -> None:
        self._provider = provider
        self._cache = cache

    def hourly_forecasts(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        window = f"{start:{HOUR_KEY_FORMAT}}-{end:{HOUR_KEY_FORMAT}}"
        keys = [f"forecast:{p.lat:.4f}:{p.lon:.4f}:{window}" for p in points]
        cached: dict[str, HourlyForecast] = self._cache.get_many(keys)

        missing = [
            (key, point) for key, point in zip(keys, points, strict=True) if key not in cached
        ]
        if missing:
            fetched = self._provider.hourly_forecasts([point for _, point in missing], start, end)
            new_entries = {
                key: forecast for (key, _), forecast in zip(missing, fetched, strict=True)
            }
            self._cache.set_many(new_entries, CACHE_SECONDS)
            cached.update(new_entries)
        return [cached[key] for key in keys]
