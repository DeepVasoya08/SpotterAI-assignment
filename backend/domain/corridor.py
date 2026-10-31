"""Grid of forecast locations covering the corridor around a trip's routes.

Cells sit on a global lattice, so the same place always maps to the same cell and
forecasts can be cached between requests. The lattice spacing is chosen per trip so the
corridor stays within a fixed number of cells: short trips get a fine grid, long ones a
coarser grid, and the forecast payload stays bounded either way.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import ceil, cos, radians, sqrt

from domain.geo import GeoPoint, haversine_miles, interpolate

MILES_PER_DEGREE_LAT = 69.0
LATTICE_STEPS_DEGREES = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0)


@dataclass(frozen=True, slots=True)
class CorridorGrid:
    step_degrees: float
    cells: tuple[GeoPoint, ...]


def corridor_grid(
    paths: Sequence[Sequence[GeoPoint]], buffer_miles: float, max_cells: int
) -> CorridorGrid:
    """Lattice cells whose centres lie within ``buffer_miles`` of any path."""
    if not any(len(path) >= 2 for path in paths):
        raise ValueError("At least one path with two points is required.")

    total_miles = sum(haversine_miles(a, b) for path in paths for a, b in pairwise(path))
    # Area of the corridor divided by the cell budget gives the ideal cell size.
    ideal_step = sqrt(total_miles * 2 * buffer_miles / max_cells) / MILES_PER_DEGREE_LAT

    steps = [step for step in LATTICE_STEPS_DEGREES if step >= ideal_step]
    for step in steps or [LATTICE_STEPS_DEGREES[-1]]:
        cells = _cells_near_paths(paths, step, buffer_miles)
        if len(cells) <= max_cells:
            break
    return CorridorGrid(step_degrees=step, cells=tuple(sorted(cells, key=_north_to_south)))


def _cells_near_paths(
    paths: Sequence[Sequence[GeoPoint]], step: float, buffer_miles: float
) -> set[GeoPoint]:
    reach_lat = ceil(buffer_miles / MILES_PER_DEGREE_LAT / step)
    keys: set[tuple[int, int]] = set()
    for point in _densify(paths, max_gap_miles=step * MILES_PER_DEGREE_LAT / 2):
        reach_lon = ceil(reach_lat / max(cos(radians(point.lat)), 0.1))
        row, col = round(point.lat / step), round(point.lon / step)
        for d_row in range(-reach_lat, reach_lat + 1):
            for d_col in range(-reach_lon, reach_lon + 1):
                key = (row + d_row, col + d_col)
                if key in keys:
                    continue
                if haversine_miles(point, _centre(key, step)) <= buffer_miles:
                    keys.add(key)
    return {_centre(key, step) for key in keys}


def _densify(paths: Sequence[Sequence[GeoPoint]], max_gap_miles: float) -> list[GeoPoint]:
    points: list[GeoPoint] = []
    for path in paths:
        if path:
            points.append(path[0])
        for a, b in pairwise(path):
            pieces = max(1, ceil(haversine_miles(a, b) / max_gap_miles))
            points.extend(interpolate(a, b, i / pieces) for i in range(1, pieces + 1))
    return points


def _centre(key: tuple[int, int], step: float) -> GeoPoint:
    row, col = key
    return GeoPoint(lat=round(row * step, 6), lon=round(col * step, 6))


def _north_to_south(point: GeoPoint) -> tuple[float, float]:
    return (-point.lat, point.lon)
