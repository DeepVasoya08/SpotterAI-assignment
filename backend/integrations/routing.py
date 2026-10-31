"""Provider-neutral types for geocoding and routing."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from domain.geo import GeoPoint
from domain.sampling import RoutePath


@dataclass(frozen=True, slots=True)
class Place:
    id: str
    label: str
    point: GeoPoint


@dataclass(frozen=True, slots=True)
class RouteOption:
    path: RoutePath
    distance_miles: float
    duration_s: float


class RoutingProvider(Protocol):
    def search_places(self, query: str, limit: int) -> list[Place]: ...

    def truck_routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        departure: datetime,
        gross_weight_lb: float,
        via: Sequence[GeoPoint] = (),
    ) -> list[RouteOption]: ...
