"""Checkpoint placement along a route.

A route is a polyline whose vertices carry the cumulative driving time from departure,
as reported by the routing provider. Checkpoints are placed every ``interval_miles``
from the origin, plus one at the destination, and their travel time is interpolated
between the surrounding vertices so each checkpoint has an estimated arrival time.

Each checkpoint stands for the stretch of road halfway to its neighbours, so the
represented miles of all checkpoints add up to the route length.
"""

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate, pairwise

from domain.geo import GeoPoint, haversine_miles, interpolate


@dataclass(frozen=True, slots=True)
class RoutePath:
    points: tuple[GeoPoint, ...]
    elapsed_s: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("A route path needs at least two points.")
        if len(self.points) != len(self.elapsed_s):
            raise ValueError("Every point needs an elapsed time.")
        if any(later < earlier for earlier, later in pairwise(self.elapsed_s)):
            raise ValueError("Elapsed time must not decrease along the route.")


@dataclass(frozen=True, slots=True)
class Checkpoint:
    distance_miles: float
    represented_miles: float
    point: GeoPoint
    elapsed_s: float


def place_checkpoints(path: RoutePath, interval_miles: float) -> list[Checkpoint]:
    if interval_miles <= 0:
        raise ValueError("Sampling interval must be positive.")

    cumulative_miles = list(
        accumulate((haversine_miles(a, b) for a, b in pairwise(path.points)), initial=0.0)
    )
    total_miles = cumulative_miles[-1]

    distances = _checkpoint_distances(total_miles, interval_miles)
    return [
        _checkpoint_at(path, cumulative_miles, distance, represented)
        for distance, represented in zip(distances, _represented_miles(distances), strict=True)
    ]


def _checkpoint_distances(total_miles: float, interval_miles: float) -> list[float]:
    count = int(total_miles // interval_miles)
    distances = [step * interval_miles for step in range(count + 1)]
    if total_miles - distances[-1] > 1e-9:
        distances.append(total_miles)
    return distances


def _represented_miles(distances: Sequence[float]) -> list[float]:
    if len(distances) == 1:
        return [0.0]
    midpoints = [(a + b) / 2 for a, b in pairwise(distances)]
    boundaries = [distances[0], *midpoints, distances[-1]]
    return [end - start for start, end in pairwise(boundaries)]


def _checkpoint_at(
    path: RoutePath, cumulative_miles: Sequence[float], distance: float, represented: float
) -> Checkpoint:
    # Index of the segment that contains ``distance``; clamped so the destination maps
    # onto the final segment.
    index = min(bisect_right(cumulative_miles, distance), len(cumulative_miles) - 1) - 1
    start_miles, end_miles = cumulative_miles[index], cumulative_miles[index + 1]
    segment_miles = end_miles - start_miles
    fraction = (distance - start_miles) / segment_miles if segment_miles else 0.0

    start_s, end_s = path.elapsed_s[index], path.elapsed_s[index + 1]
    return Checkpoint(
        distance_miles=distance,
        represented_miles=represented,
        point=interpolate(path.points[index], path.points[index + 1], fraction),
        elapsed_s=start_s + (end_s - start_s) * fraction,
    )
