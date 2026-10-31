import pytest

from domain.geo import GeoPoint, haversine_miles, interpolate


def test_haversine_matches_known_city_distance() -> None:
    new_york = GeoPoint(40.7128, -74.0060)
    los_angeles = GeoPoint(34.0522, -118.2437)

    assert haversine_miles(new_york, los_angeles) == pytest.approx(2445, rel=0.005)


def test_haversine_of_same_point_is_zero() -> None:
    point = GeoPoint(35.0, -97.0)

    assert haversine_miles(point, point) == 0


def test_interpolate_returns_fractional_point() -> None:
    midpoint = interpolate(GeoPoint(0, 0), GeoPoint(10, -20), 0.25)

    assert midpoint == GeoPoint(2.5, -5)
