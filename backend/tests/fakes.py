"""In-memory stand-ins for the routing and weather providers."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import accumulate, pairwise

from domain.forecast import HourlyForecast
from domain.geo import GeoPoint, haversine_miles
from domain.sampling import RoutePath
from integrations.errors import ProviderError
from integrations.routing import Place, RouteOption

FORECAST_HOURS = 72


def straight_route(points: Sequence[GeoPoint], speed_mph: float = 60) -> RouteOption:
    """A route through ``points`` driven at a constant speed."""
    segment_miles = [haversine_miles(a, b) for a, b in pairwise(points)]
    elapsed = [0.0, *accumulate(miles / speed_mph * 3600 for miles in segment_miles)]
    distance = sum(segment_miles)
    return RouteOption(
        path=RoutePath(points=tuple(points), elapsed_s=tuple(elapsed)),
        distance_miles=distance,
        duration_s=elapsed[-1],
    )


def east_west_route(lat: float, start_lon: float = -100, end_lon: float = -98) -> RouteOption:
    steps = 40
    return straight_route(
        [GeoPoint(lat, start_lon + (end_lon - start_lon) * i / steps) for i in range(steps + 1)]
    )


@dataclass
class FakeRouting:
    primary: list[RouteOption]
    detours: list[RouteOption | ProviderError] = field(default_factory=list)
    places: list[Place] = field(default_factory=list)
    via_requests: list[GeoPoint] = field(default_factory=list)
    place_queries: list[str] = field(default_factory=list)

    def search_places(self, query: str, limit: int) -> list[Place]:
        self.place_queries.append(query)
        return self.places[:limit]

    def truck_routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        departure: datetime,
        gross_weight_lb: float,
        via: Sequence[GeoPoint] = (),
    ) -> list[RouteOption]:
        if not via:
            return self.primary
        self.via_requests.append(via[0])
        index = len(self.via_requests) - 1
        if index >= len(self.detours):
            return []
        detour = self.detours[index]
        if isinstance(detour, ProviderError):
            raise detour
        return [detour]


WeatherFunction = Callable[[GeoPoint, int], tuple[float, float, float]]
"""Returns (gust mph, rain in/hr, snow in/hr) for a point and hour offset."""


def calm(point: GeoPoint, hour: int) -> tuple[float, float, float]:
    return (5.0, 0.0, 0.0)


@dataclass
class FakeWeather:
    weather: WeatherFunction = calm
    requested_points: list[GeoPoint] = field(default_factory=list)

    def hourly_forecasts(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        self.requested_points.extend(points)
        first_hour = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        return [self._forecast(point, first_hour) for point in points]

    def _forecast(self, point: GeoPoint, start: datetime) -> HourlyForecast:
        hours = [self.weather(point, hour) for hour in range(FORECAST_HOURS)]
        return HourlyForecast(
            point=point,
            start=start,
            wind_speed_mph=tuple(gust * 0.6 for gust, _, _ in hours),
            wind_gust_mph=tuple(gust for gust, _, _ in hours),
            rain_in=tuple(rain for _, rain, _ in hours),
            snow_in=tuple(snow for _, _, snow in hours),
        )


DEPARTURE = datetime(2026, 11, 2, 8, tzinfo=UTC)
ONE_HOUR = timedelta(hours=1)
