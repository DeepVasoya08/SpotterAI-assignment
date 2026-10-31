"""Hour-by-hour weather risk across the corridor around a trip's routes."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.corridor import corridor_grid
from domain.geo import GeoPoint
from domain.risk import RiskLevel, WeatherConditions, assess
from services.trip_planner import WeatherProvider

CORRIDOR_BUFFER_MILES = 30
MAX_CORRIDOR_CELLS = 300
FORECAST_HOURS = 48


@dataclass(frozen=True, slots=True)
class CorridorCell:
    point: GeoPoint
    conditions: tuple[WeatherConditions, ...]
    levels: tuple[RiskLevel, ...]


@dataclass(frozen=True, slots=True)
class CorridorForecast:
    start: datetime
    step_degrees: float
    cells: tuple[CorridorCell, ...]


class CorridorForecaster:
    def __init__(self, weather: WeatherProvider) -> None:
        self._weather = weather

    def forecast(
        self, paths: Sequence[Sequence[GeoPoint]], departure: datetime, load_weight_lb: float
    ) -> CorridorForecast:
        """Conditions and risk for every cell at departure + 0..48 hours.

        Risk uses the trip's load weight, so the heatmap matches the route assessment.
        """
        grid = corridor_grid(paths, CORRIDOR_BUFFER_MILES, MAX_CORRIDOR_CELLS)
        moments = [departure + timedelta(hours=hour) for hour in range(FORECAST_HOURS + 1)]
        forecasts = self._weather.hourly_forecasts(grid.cells, moments[0], moments[-1])

        cells = []
        for point, forecast in zip(grid.cells, forecasts, strict=True):
            conditions = tuple(forecast.conditions_at(moment) for moment in moments)
            cells.append(
                CorridorCell(
                    point=point,
                    conditions=conditions,
                    levels=tuple(assess(c, load_weight_lb).level for c in conditions),
                )
            )
        return CorridorForecast(start=departure, step_degrees=grid.step_degrees, cells=tuple(cells))
