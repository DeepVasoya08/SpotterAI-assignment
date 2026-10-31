import pytest

from domain.corridor import LATTICE_STEPS_DEGREES, corridor_grid
from domain.geo import GeoPoint, haversine_miles

EASTBOUND = [GeoPoint(40, -100), GeoPoint(40, -96)]


def distance_to_path(point: GeoPoint, path: list[GeoPoint], samples: int = 400) -> float:
    start, end = path[0], path[-1]
    return min(
        haversine_miles(
            point,
            GeoPoint(
                start.lat + (end.lat - start.lat) * i / samples,
                start.lon + (end.lon - start.lon) * i / samples,
            ),
        )
        for i in range(samples + 1)
    )


def test_cells_lie_within_buffer_of_the_path() -> None:
    grid = corridor_grid([EASTBOUND], buffer_miles=30, max_cells=300)

    assert grid.cells
    assert all(distance_to_path(cell, EASTBOUND) <= 30.5 for cell in grid.cells)


def test_corridor_covers_the_whole_path() -> None:
    grid = corridor_grid([EASTBOUND], buffer_miles=30, max_cells=300)

    lons = [cell.lon for cell in grid.cells]
    assert min(lons) <= -100
    assert max(lons) >= -96


def test_cells_sit_on_the_lattice() -> None:
    grid = corridor_grid([EASTBOUND], buffer_miles=30, max_cells=300)

    for cell in grid.cells:
        assert cell.lat / grid.step_degrees == pytest.approx(round(cell.lat / grid.step_degrees))
        assert cell.lon / grid.step_degrees == pytest.approx(round(cell.lon / grid.step_degrees))


@pytest.mark.parametrize("max_cells", [50, 150, 300])
def test_respects_the_cell_budget(max_cells: int) -> None:
    long_trip = [GeoPoint(41.9, -87.6), GeoPoint(39.7, -105.0), GeoPoint(34.0, -118.2)]

    grid = corridor_grid([long_trip], buffer_miles=30, max_cells=max_cells)

    assert 0 < len(grid.cells) <= max_cells


def test_longer_trips_use_a_coarser_grid() -> None:
    short = corridor_grid([[GeoPoint(40, -100), GeoPoint(40, -99)]], 30, 300)
    long = corridor_grid([[GeoPoint(40, -120), GeoPoint(40, -75)]], 30, 300)

    assert short.step_degrees < long.step_degrees
    assert short.step_degrees == LATTICE_STEPS_DEGREES[0]


def test_overlapping_routes_share_cells() -> None:
    single = corridor_grid([EASTBOUND], 30, 300)
    doubled = corridor_grid([EASTBOUND, EASTBOUND], 30, 300)

    assert set(doubled.cells) >= set(single.cells)
    assert len(set(doubled.cells)) == len(doubled.cells)


def test_requires_a_path() -> None:
    with pytest.raises(ValueError, match="two points"):
        corridor_grid([[GeoPoint(40, -100)]], 30, 300)
