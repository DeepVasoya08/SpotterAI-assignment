"""Hourly forecast series for a single location.

Wind is an instantaneous value at each hour, so the nearest hour is used. Rain and snow
are totals for the hour ending at each timestamp, so a moment uses the hour whose
period contains it. Those totals are the in/hr rates the risk rules expect.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from domain.geo import GeoPoint
from domain.risk import WeatherConditions

ONE_HOUR = timedelta(hours=1)


class ForecastUnavailableError(ValueError):
    """The requested moment is outside the forecast's time range."""


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    point: GeoPoint
    start: datetime
    wind_speed_mph: tuple[float, ...]
    wind_gust_mph: tuple[float, ...]
    rain_in: tuple[float, ...]
    snow_in: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.start.tzinfo is None:
            raise ValueError("Forecast start must be timezone-aware.")
        lengths = {
            len(self.wind_speed_mph),
            len(self.wind_gust_mph),
            len(self.rain_in),
            len(self.snow_in),
        }
        if len(lengths) != 1:
            raise ValueError("All hourly series must have the same length.")

    @property
    def hours(self) -> int:
        return len(self.wind_speed_mph)

    def conditions_at(self, moment: datetime) -> WeatherConditions:
        offset_hours = (moment - self.start) / ONE_HOUR
        wind_index = self._index(round(offset_hours), moment)
        precipitation_index = self._index(ceil(offset_hours), moment)
        return WeatherConditions(
            wind_speed_mph=self.wind_speed_mph[wind_index],
            wind_gust_mph=self.wind_gust_mph[wind_index],
            rain_in_per_hr=self.rain_in[precipitation_index],
            snow_in_per_hr=self.snow_in[precipitation_index],
        )

    def _index(self, index: int, moment: datetime) -> int:
        if not 0 <= index < self.hours:
            raise ForecastUnavailableError(f"No forecast for {moment.isoformat()}.")
        return index
