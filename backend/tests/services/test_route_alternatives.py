import pytest

from domain.geo import GeoPoint
from services.route_alternatives import (
    detour_via_points,
    select_distinct_routes,
    shared_road_ratio,
)
from tests.fakes import east_west_route


def test_detour_points_sit_either_side_of_an_eastbound_trip() -> None:
    via_points = detour_via_points(GeoPoint(40, -100), GeoPoint(40, -90))

    assert [round(p.lon, 6) for p in via_points] == [-95.0] * 4
    assert via_points[0].lat > 40 > via_points[1].lat
    assert via_points[2].lat > via_points[0].lat


def test_detour_points_sit_either_side_of_a_northbound_trip() -> None:
    via_points = detour_via_points(GeoPoint(30, -95), GeoPoint(40, -95))

    assert [round(p.lat, 6) for p in via_points] == [35.0] * 4
    # Left of a northbound trip is west.
    assert via_points[0].lon < -95 < via_points[1].lon


def test_shared_road_ratio() -> None:
    route = east_west_route(lat=40)

    assert shared_road_ratio(route.path, route.path) == 1
    assert shared_road_ratio(route.path, east_west_route(lat=41).path) == 0
    half = east_west_route(lat=40, start_lon=-99, end_lon=-98)
    assert shared_road_ratio(route.path, half.path) == pytest.approx(0.5, abs=0.1)


def test_keeps_provider_routes_first_then_distinct_detours() -> None:
    primary = [east_west_route(lat=40)]
    duplicate = east_west_route(lat=40.001)
    detour_a = east_west_route(lat=41)
    detour_b = east_west_route(lat=39)
    extra = east_west_route(lat=42)

    chosen = select_distinct_routes(primary, [duplicate, None, detour_a, detour_b, extra])

    assert chosen == [primary[0], detour_a, detour_b]


def test_drops_duplicate_provider_routes() -> None:
    route = east_west_route(lat=40)

    assert select_distinct_routes([route, route], []) == [route]
