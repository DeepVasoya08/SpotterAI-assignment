"""Ensure the driver is offered up to three genuinely different routes.

Truck routing often returns fewer than three alternatives, especially on long trips.
When that happens, extra candidates are forced through a via point offset to either
side of the straight line between origin and destination. Candidates that mostly share
road with a route already chosen are discarded.
"""

from collections.abc import Sequence
from math import cos, radians

from domain.geo import GeoPoint
from domain.sampling import RoutePath
from integrations.routing import RouteOption

TARGET_ROUTE_COUNT = 3
# Offsets as a fraction of the origin-destination distance; positive is to the left.
DETOUR_OFFSETS = (0.15, -0.15, 0.3, -0.3)
MAX_SHARED_ROAD = 0.85
# Roughly 2.5 miles; coarse enough that parallel lanes of the same highway match.
OVERLAP_CELL_DEGREES = 0.035


def detour_via_points(origin: GeoPoint, destination: GeoPoint) -> list[GeoPoint]:
    """Points perpendicular to the midpoint of the origin-destination line."""
    mid_lat = (origin.lat + destination.lat) / 2
    mid_lon = (origin.lon + destination.lon) / 2
    # Work in a locally flat frame where one unit is the same distance on both axes.
    lon_scale = cos(radians(mid_lat))
    d_east = (destination.lon - origin.lon) * lon_scale
    d_north = destination.lat - origin.lat
    return [
        GeoPoint(lat=mid_lat + d_east * offset, lon=mid_lon - d_north * offset / lon_scale)
        for offset in DETOUR_OFFSETS
    ]


def shared_road_ratio(path: RoutePath, other: RoutePath) -> float:
    """Fraction of ``path`` that runs through the same map cells as ``other``."""
    cells = _cells(path)
    return len(cells & _cells(other)) / len(cells) if cells else 1.0


def is_distinct(candidate: RouteOption, chosen: Sequence[RouteOption]) -> bool:
    return all(
        shared_road_ratio(candidate.path, existing.path) < MAX_SHARED_ROAD
        and shared_road_ratio(existing.path, candidate.path) < MAX_SHARED_ROAD
        for existing in chosen
    )


def select_distinct_routes(
    primary: Sequence[RouteOption],
    detours: Sequence[RouteOption | None],
) -> list[RouteOption]:
    """Keep provider routes first, then fill up with distinct detours."""
    chosen: list[RouteOption] = []
    for candidate in [*primary, *detours]:
        if len(chosen) == TARGET_ROUTE_COUNT:
            break
        if candidate is not None and is_distinct(candidate, chosen):
            chosen.append(candidate)
    return chosen


def _cells(path: RoutePath) -> set[tuple[int, int]]:
    return {
        (int(point.lat // OVERLAP_CELL_DEGREES), int(point.lon // OVERLAP_CELL_DEGREES))
        for point in path.points
    }
