from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MILES = 3958.8


@dataclass(frozen=True, slots=True)
class GeoPoint:
    lat: float
    lon: float


def haversine_miles(a: GeoPoint, b: GeoPoint) -> float:
    lat1, lat2 = radians(a.lat), radians(b.lat)
    d_lat = lat2 - lat1
    d_lon = radians(b.lon - a.lon)
    h = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * asin(sqrt(h))


def interpolate(a: GeoPoint, b: GeoPoint, fraction: float) -> GeoPoint:
    """Linear interpolation; accurate enough between consecutive route vertices."""
    return GeoPoint(lat=a.lat + (b.lat - a.lat) * fraction, lon=a.lon + (b.lon - a.lon) * fraction)
