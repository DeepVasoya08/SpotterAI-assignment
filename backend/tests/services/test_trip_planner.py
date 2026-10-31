import pytest

from domain.geo import GeoPoint
from domain.recommendation import RankingCriterion
from domain.risk import Hazard, RiskLevel
from integrations.errors import ProviderError
from integrations.routing import RouteOption
from services.trip_planner import NoRouteFoundError, TripPlanner, TripRequest
from tests.fakes import DEPARTURE, FakeRouting, FakeWeather, east_west_route

ORIGIN = GeoPoint(40, -100)
DESTINATION = GeoPoint(40, -98)


def request(load_weight_lb: float = 30_000, interval: float = 10) -> TripRequest:
    return TripRequest(
        origin=ORIGIN,
        destination=DESTINATION,
        departure=DEPARTURE,
        load_weight_lb=load_weight_lb,
        sampling_interval_miles=interval,
    )


def three_routes() -> list[RouteOption]:
    return [east_west_route(lat=40), east_west_route(lat=40.5), east_west_route(lat=39.5)]


def test_plans_every_provider_route_without_detours() -> None:
    routing = FakeRouting(primary=three_routes())

    plan = TripPlanner(routing, FakeWeather()).plan(request())

    assert [route.id for route in plan.routes] == ["route-1", "route-2", "route-3"]
    assert routing.via_requests == []


def test_adds_distinct_detours_when_provider_returns_one_route() -> None:
    routing = FakeRouting(
        primary=[east_west_route(lat=40)],
        detours=[
            east_west_route(lat=40.001),
            ProviderError("HERE", "no route"),
            east_west_route(lat=39),
            east_west_route(lat=41),
        ],
    )

    plan = TripPlanner(routing, FakeWeather()).plan(request())

    assert len(routing.via_requests) == 4
    assert [route.option.path.points[0].lat for route in plan.routes] == [40, 39, 41]


def test_raises_when_no_route_exists() -> None:
    with pytest.raises(NoRouteFoundError):
        TripPlanner(FakeRouting(primary=[]), FakeWeather()).plan(request())


def test_checkpoints_cover_the_route_with_arrival_times() -> None:
    plan = TripPlanner(FakeRouting(primary=three_routes()), FakeWeather()).plan(request())

    route = plan.routes[0]
    assert route.checkpoints[0].eta == DEPARTURE
    assert route.checkpoints[0].checkpoint.distance_miles == 0
    assert sum(cw.checkpoint.represented_miles for cw in route.checkpoints) == pytest.approx(
        route.option.distance_miles
    )
    assert route.arrival == DEPARTURE + (route.checkpoints[-1].eta - DEPARTURE)
    etas = [cw.eta for cw in route.checkpoints]
    assert etas == sorted(etas)


def test_weather_is_read_at_each_checkpoint_arrival_time() -> None:
    # Snow starts two hours after departure; the ~105 mile trip at 60 mph reaches
    # the destination after that, so only the later checkpoints see it.
    weather = FakeWeather(weather=lambda point, hour: (5, 0, 2.5 if hour >= 2 else 0))

    plan = TripPlanner(FakeRouting(primary=[east_west_route(lat=40)]), weather).plan(request())

    levels = [cw.assessment.level for cw in plan.routes[0].checkpoints]
    assert levels[0] is RiskLevel.LOW
    assert levels[-1] is RiskLevel.SEVERE
    assert plan.routes[0].checkpoints[-1].assessment.causes == (Hazard.SNOW,)


def test_heavy_load_escalates_wind_risk() -> None:
    weather = FakeWeather(weather=lambda point, hour: (40, 0, 0))
    routing = FakeRouting(primary=[east_west_route(lat=40)])

    light = TripPlanner(routing, weather).plan(request(load_weight_lb=20_000))
    heavy = TripPlanner(routing, weather).plan(request(load_weight_lb=45_000))

    assert light.routes[0].checkpoints[0].assessment.level is RiskLevel.HIGH
    assert heavy.routes[0].checkpoints[0].assessment.level is RiskLevel.SEVERE


def test_recommends_the_route_avoiding_severe_weather() -> None:
    # A storm sits over the northern route only.
    weather = FakeWeather(weather=lambda point, hour: (50, 0, 0) if point.lat > 40.2 else (5, 0, 0))
    routing = FakeRouting(primary=[east_west_route(lat=40.5), east_west_route(lat=40)])

    plan = TripPlanner(routing, weather).plan(request(load_weight_lb=20_000))

    assert plan.recommendation.route_id == "route-2"
    assert plan.recommendation.decided_by is RankingCriterion.FEWER_SEVERE_MILES


def test_nearby_checkpoints_share_a_forecast() -> None:
    weather = FakeWeather()
    routing = FakeRouting(primary=[east_west_route(lat=40), east_west_route(lat=40.001)])

    TripPlanner(routing, weather).plan(request())

    checkpoints_per_route = 12
    assert len(weather.requested_points) == checkpoints_per_route
