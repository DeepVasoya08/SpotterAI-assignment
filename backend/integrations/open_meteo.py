"""Open-Meteo hourly forecast client.

One request carries many locations, so checkpoints are fetched in chunks rather than
one call each. Responses are requested in mph and inches, matching the risk rules.
"""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from itertools import batched
from typing import Any

import httpx

from domain.forecast import HourlyForecast
from domain.geo import GeoPoint
from integrations.errors import ProviderError

PROVIDER = "Open-Meteo"
BASE_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")
LOCATIONS_PER_REQUEST = 100
MAX_CONCURRENT_REQUESTS = 4
HOUR_FORMAT = "%Y-%m-%dT%H:%M"


class OpenMeteoClient:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def hourly_forecasts(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        """Forecasts for each point, in input order, covering whole hours start..end."""
        first_hour = _floor_hour(start)
        last_hour = _floor_hour(end) + timedelta(hours=1)
        chunks = list(batched(points, LOCATIONS_PER_REQUEST, strict=False))

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            results = executor.map(lambda chunk: self._fetch(chunk, first_hour, last_hour), chunks)
            return [forecast for chunk_result in results for forecast in chunk_result]

    def _fetch(
        self, points: Sequence[GeoPoint], first_hour: datetime, last_hour: datetime
    ) -> list[HourlyForecast]:
        params = {
            "latitude": ",".join(f"{p.lat:.4f}" for p in points),
            "longitude": ",".join(f"{p.lon:.4f}" for p in points),
            "hourly": ",".join(HOURLY_VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "start_hour": first_hour.strftime(HOUR_FORMAT),
            "end_hour": last_hour.strftime(HOUR_FORMAT),
        }
        try:
            response = self._http.get(BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ProviderError(PROVIDER, _error_reason(error.response)) from error
        except httpx.HTTPError as error:
            raise ProviderError(PROVIDER, "request failed") from error

        payload = response.json()
        # A single location comes back as an object, several as a list.
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(points):
            raise ProviderError(PROVIDER, "unexpected number of locations in response")
        return [
            _parse_location(point, location, first_hour)
            for point, location in zip(points, locations, strict=True)
        ]


def _parse_location(point: GeoPoint, location: dict[str, Any], start: datetime) -> HourlyForecast:
    try:
        hourly = location["hourly"]
        rain = _series(hourly["rain"])
        showers = _series(hourly["showers"])
        return HourlyForecast(
            point=point,
            start=start,
            wind_speed_mph=_series(hourly["wind_speed_10m"]),
            wind_gust_mph=_series(hourly["wind_gusts_10m"]),
            rain_in=tuple(r + s for r, s in zip(rain, showers, strict=True)),
            snow_in=_series(hourly["snowfall"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderError(PROVIDER, "malformed forecast response") from error


def _series(values: Sequence[float | None]) -> tuple[float, ...]:
    # Open-Meteo returns null where a model has no value; treat it as no weather.
    return tuple(float(value) if value is not None else 0.0 for value in values)


def _floor_hour(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _error_reason(response: httpx.Response) -> str:
    try:
        reason = response.json().get("reason")
    except ValueError:
        reason = None
    return f"HTTP {response.status_code}" + (f": {reason}" if reason else "")
