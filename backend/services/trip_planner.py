"""Plan a trip: fetch route options, sample weather along each and recommend one."""

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from domain.forecast import HourlyForecast
from domain.geo import GeoPoint
from domain.recommendation import Recommendation, RiskSegment, RouteRiskProfile, recommend
from domain.risk import RiskAssessment, WeatherConditions, assess
from domain.sampling import Checkpoint, place_checkpoints
from integrations.errors import ProviderError
from integrations.routing import RouteOption, RoutingProvider
from services.route_alternatives import detour_via_points, select_distinct_routes

logger = logging.getLogger(__name__)

# Checkpoints closer than this share one forecast; well within weather model resolution.
FORECAST_GRID_DEGREES = 0.02


class WeatherProvider(Protocol):
    def hourly_forecasts(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlyForecast]: ...


class NoRouteFoundError(Exception):
    """The routing provider found no truck route between the two places."""


@dataclass(frozen=True, slots=True)
class TripRequest:
    origin: GeoPoint
    destination: GeoPoint
    departure: datetime
    load_weight_lb: float
    sampling_interval_miles: float


@dataclass(frozen=True, slots=True)
class CheckpointWeather:
    checkpoint: Checkpoint
    eta: datetime
    conditions: WeatherConditions
    assessment: RiskAssessment


@dataclass(frozen=True, slots=True)
class PlannedRoute:
    id: str
    option: RouteOption
    checkpoints: tuple[CheckpointWeather, ...]
    profile: RouteRiskProfile

    @property
    def arrival(self) -> datetime:
        return self.checkpoints[-1].eta


@dataclass(frozen=True, slots=True)
class TripPlan:
    request: TripRequest
    routes: tuple[PlannedRoute, ...]
    recommendation: Recommendation


class TripPlanner:
    def __init__(self, routing: RoutingProvider, weather: WeatherProvider) -> None:
        self._routing = routing
        self._weather = weather

    def plan(self, request: TripRequest) -> TripPlan:
        options = self._route_options(request)
        sampled = [
            place_checkpoints(option.path, request.sampling_interval_miles) for option in options
        ]
        forecast_for = self._forecasts(request.departure, [cp for route in sampled for cp in route])

        routes = tuple(
            self._planned_route(f"route-{index + 1}", option, checkpoints, request, forecast_for)
            for index, (option, checkpoints) in enumerate(zip(options, sampled, strict=True))
        )
        return TripPlan(
            request=request,
            routes=routes,
            recommendation=recommend([route.profile for route in routes]),
        )

    def _route_options(self, request: TripRequest) -> list[RouteOption]:
        primary = self._routing.truck_routes(
            request.origin, request.destination, request.departure, request.load_weight_lb
        )
        if not primary:
            raise NoRouteFoundError
        detours = (
            self._detour_routes(request) if len(select_distinct_routes(primary, [])) < 3 else []
        )
        return select_distinct_routes(primary, detours)

    def _detour_routes(self, request: TripRequest) -> list[RouteOption | None]:
        def fetch(via: GeoPoint) -> RouteOption | None:
            try:
                routes = self._routing.truck_routes(
                    request.origin,
                    request.destination,
                    request.departure,
                    request.load_weight_lb,
                    via=(via,),
                )
            except ProviderError:
                # A via point in a lake or with no truck access is expected; skip it.
                logger.info("Detour route via %s unavailable", via)
                return None
            return routes[0] if routes else None

        via_points = detour_via_points(request.origin, request.destination)
        with ThreadPoolExecutor(max_workers=len(via_points)) as executor:
            return list(executor.map(fetch, via_points))

    def _forecasts(
        self, departure: datetime, checkpoints: Sequence[Checkpoint]
    ) -> dict[tuple[int, int], HourlyForecast]:
        unique: dict[tuple[int, int], GeoPoint] = {}
        for checkpoint in checkpoints:
            unique.setdefault(_grid_key(checkpoint.point), checkpoint.point)

        latest = departure + timedelta(seconds=max(cp.elapsed_s for cp in checkpoints))
        forecasts = self._weather.hourly_forecasts(list(unique.values()), departure, latest)
        return dict(zip(unique, forecasts, strict=True))

    def _planned_route(
        self,
        route_id: str,
        option: RouteOption,
        checkpoints: Sequence[Checkpoint],
        request: TripRequest,
        forecast_for: dict[tuple[int, int], HourlyForecast],
    ) -> PlannedRoute:
        weather: list[CheckpointWeather] = []
        for checkpoint in checkpoints:
            eta = request.departure + timedelta(seconds=checkpoint.elapsed_s)
            conditions = forecast_for[_grid_key(checkpoint.point)].conditions_at(eta)
            weather.append(
                CheckpointWeather(
                    checkpoint=checkpoint,
                    eta=eta,
                    conditions=conditions,
                    assessment=assess(conditions, request.load_weight_lb),
                )
            )

        profile = RouteRiskProfile.from_segments(
            route_id,
            option.duration_s,
            [RiskSegment(cw.checkpoint.represented_miles, cw.assessment.level) for cw in weather],
        )
        return PlannedRoute(id=route_id, option=option, checkpoints=tuple(weather), profile=profile)


def _grid_key(point: GeoPoint) -> tuple[int, int]:
    return round(point.lat / FORECAST_GRID_DEGREES), round(point.lon / FORECAST_GRID_DEGREES)
