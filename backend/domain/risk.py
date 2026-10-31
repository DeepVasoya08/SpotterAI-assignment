"""Weather risk classification for a single checkpoint.

Thresholds come from the assessment brief. Bands include their lower bound, so 25 mph
is Moderate and 0.25 in/hr of rain is High. "No Travel" for rain and snow is written as
strictly greater than the Severe ceiling (>1.00 in/hr, >3.0 in/hr) and is kept that way.
"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


class Hazard(StrEnum):
    WIND = "wind"
    RAIN = "rain"
    SNOW = "snow"


@dataclass(frozen=True, slots=True)
class Threshold:
    level: RiskLevel
    minimum: float
    inclusive: bool = True

    def is_met_by(self, value: float) -> bool:
        return value >= self.minimum if self.inclusive else value > self.minimum


# Ordered from most to least severe; the first threshold met decides the level.
WIND_THRESHOLDS_MPH = (
    Threshold(RiskLevel.NO_TRAVEL, 55),
    Threshold(RiskLevel.SEVERE, 45),
    Threshold(RiskLevel.HIGH, 35),
    Threshold(RiskLevel.MODERATE, 25),
)
RAIN_THRESHOLDS_IN_PER_HR = (
    Threshold(RiskLevel.NO_TRAVEL, 1.00, inclusive=False),
    Threshold(RiskLevel.SEVERE, 0.50),
    Threshold(RiskLevel.HIGH, 0.25),
    Threshold(RiskLevel.MODERATE, 0.10),
)
SNOW_THRESHOLDS_IN_PER_HR = (
    Threshold(RiskLevel.NO_TRAVEL, 3.0, inclusive=False),
    Threshold(RiskLevel.SEVERE, 2.0),
    Threshold(RiskLevel.HIGH, 1.0),
    Threshold(RiskLevel.MODERATE, 0.5),
)

SEVERE_WIND_NO_TRAVEL_LOAD_LB = 30_000
HIGH_WIND_SEVERE_LOAD_LB = 40_000


@dataclass(frozen=True, slots=True)
class WeatherConditions:
    wind_speed_mph: float
    wind_gust_mph: float
    rain_in_per_hr: float
    snow_in_per_hr: float

    @property
    def effective_wind_mph(self) -> float:
        """Wind used for classification: gusts, which are what push a high-sided trailer."""
        return max(self.wind_speed_mph, self.wind_gust_mph)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    hazard_levels: dict[Hazard, RiskLevel]
    load_adjusted: bool

    @property
    def causes(self) -> tuple[Hazard, ...]:
        """Hazards responsible for the overall level; empty when the level is Low."""
        if self.level is RiskLevel.LOW:
            return ()
        return tuple(hazard for hazard, level in self.hazard_levels.items() if level == self.level)


def classify(value: float, thresholds: tuple[Threshold, ...]) -> RiskLevel:
    for threshold in thresholds:
        if threshold.is_met_by(value):
            return threshold.level
    return RiskLevel.LOW


def apply_load_rules(wind_level: RiskLevel, load_weight_lb: float) -> RiskLevel:
    """Escalate the wind level for heavy loads (45-54 mph is Severe, 35-44 mph is High)."""
    if wind_level is RiskLevel.SEVERE and load_weight_lb > SEVERE_WIND_NO_TRAVEL_LOAD_LB:
        return RiskLevel.NO_TRAVEL
    if wind_level is RiskLevel.HIGH and load_weight_lb > HIGH_WIND_SEVERE_LOAD_LB:
        return RiskLevel.SEVERE
    return wind_level


def assess(conditions: WeatherConditions, load_weight_lb: float) -> RiskAssessment:
    base_wind_level = classify(conditions.effective_wind_mph, WIND_THRESHOLDS_MPH)
    wind_level = apply_load_rules(base_wind_level, load_weight_lb)
    hazard_levels = {
        Hazard.WIND: wind_level,
        Hazard.RAIN: classify(conditions.rain_in_per_hr, RAIN_THRESHOLDS_IN_PER_HR),
        Hazard.SNOW: classify(conditions.snow_in_per_hr, SNOW_THRESHOLDS_IN_PER_HR),
    }
    return RiskAssessment(
        level=max(hazard_levels.values()),
        hazard_levels=hazard_levels,
        load_adjusted=wind_level is not base_wind_level,
    )
