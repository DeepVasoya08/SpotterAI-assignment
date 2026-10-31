import pytest

from domain.geo import GeoPoint, haversine_miles
from domain.sampling import RoutePath, place_checkpoints

MILES_PER_DEGREE_LAT = haversine_miles(GeoPoint(0, 0), GeoPoint(1, 0))
SPEED_MPH = 60


def northbound_path(degrees: float, steps: int = 100) -> RoutePath:
    """A straight route along a meridian, driven at a constant 60 mph."""
    points = tuple(GeoPoint(degrees * i / steps, 0) for i in range(steps + 1))
    elapsed = tuple(haversine_miles(points[0], point) / SPEED_MPH * 3600 for point in points)
    return RoutePath(points=points, elapsed_s=elapsed)


class TestPlaceCheckpoints:
    def test_places_checkpoints_every_interval_plus_destination(self) -> None:
        path = northbound_path(1)

        checkpoints = place_checkpoints(path, interval_miles=25)

        assert [round(c.distance_miles, 2) for c in checkpoints] == [
            0,
            25,
            50,
            round(MILES_PER_DEGREE_LAT, 2),
        ]

    def test_does_not_duplicate_destination_on_exact_multiple(self) -> None:
        path = RoutePath(
            points=(GeoPoint(0, 0), GeoPoint(1, 0)),
            elapsed_s=(0, 3600),
        )

        checkpoints = place_checkpoints(path, interval_miles=MILES_PER_DEGREE_LAT / 2)

        assert len(checkpoints) == 3

    @pytest.mark.parametrize("interval", [10, 25, 50])
    def test_represented_miles_add_up_to_route_length(self, interval: float) -> None:
        checkpoints = place_checkpoints(northbound_path(3), interval_miles=interval)

        assert sum(c.represented_miles for c in checkpoints) == pytest.approx(
            3 * MILES_PER_DEGREE_LAT
        )

    def test_each_checkpoint_represents_half_way_to_its_neighbours(self) -> None:
        checkpoints = place_checkpoints(northbound_path(1), interval_miles=25)
        last_gap = MILES_PER_DEGREE_LAT - 50

        assert [c.represented_miles for c in checkpoints] == pytest.approx(
            [12.5, 25, 12.5 + last_gap / 2, last_gap / 2]
        )

    def test_checkpoint_position_is_interpolated_along_the_route(self) -> None:
        checkpoints = place_checkpoints(northbound_path(1, steps=3), interval_miles=25)

        assert checkpoints[1].point.lat == pytest.approx(25 / MILES_PER_DEGREE_LAT)
        assert checkpoints[-1].point == GeoPoint(1, 0)

    def test_elapsed_time_follows_constant_speed(self) -> None:
        checkpoints = place_checkpoints(northbound_path(1), interval_miles=10)

        for checkpoint in checkpoints:
            assert checkpoint.elapsed_s == pytest.approx(
                checkpoint.distance_miles / SPEED_MPH * 3600
            )

    def test_elapsed_time_reflects_slower_segments(self) -> None:
        # The first half takes three hours, the second half one hour.
        path = RoutePath(
            points=(GeoPoint(0, 0), GeoPoint(0.5, 0), GeoPoint(1, 0)),
            elapsed_s=(0, 3 * 3600, 4 * 3600),
        )
        quarter = MILES_PER_DEGREE_LAT / 4

        checkpoints = place_checkpoints(path, interval_miles=quarter)

        assert [c.elapsed_s / 3600 for c in checkpoints] == pytest.approx([0, 1.5, 3, 3.5, 4])

    def test_route_shorter_than_interval_has_origin_and_destination(self) -> None:
        checkpoints = place_checkpoints(northbound_path(0.1), interval_miles=50)

        assert len(checkpoints) == 2
        assert checkpoints[0].distance_miles == 0

    def test_rejects_non_positive_interval(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            place_checkpoints(northbound_path(1), interval_miles=0)


class TestRoutePath:
    def test_requires_two_points(self) -> None:
        with pytest.raises(ValueError, match="two points"):
            RoutePath(points=(GeoPoint(0, 0),), elapsed_s=(0,))

    def test_requires_elapsed_time_per_point(self) -> None:
        with pytest.raises(ValueError, match="elapsed time"):
            RoutePath(points=(GeoPoint(0, 0), GeoPoint(1, 0)), elapsed_s=(0,))

    def test_rejects_decreasing_elapsed_time(self) -> None:
        with pytest.raises(ValueError, match="must not decrease"):
            RoutePath(points=(GeoPoint(0, 0), GeoPoint(1, 0)), elapsed_s=(10, 5))
