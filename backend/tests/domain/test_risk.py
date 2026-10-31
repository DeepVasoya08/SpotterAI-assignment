import pytest

from domain.risk import (
    RAIN_THRESHOLDS_IN_PER_HR,
    SNOW_THRESHOLDS_IN_PER_HR,
    WIND_THRESHOLDS_MPH,
    Hazard,
    RiskLevel,
    WeatherConditions,
    apply_load_rules,
    assess,
    classify,
)

LOW = RiskLevel.LOW
MODERATE = RiskLevel.MODERATE
HIGH = RiskLevel.HIGH
SEVERE = RiskLevel.SEVERE
NO_TRAVEL = RiskLevel.NO_TRAVEL


def conditions(
    wind: float = 0, gust: float = 0, rain: float = 0, snow: float = 0
) -> WeatherConditions:
    return WeatherConditions(
        wind_speed_mph=wind, wind_gust_mph=gust, rain_in_per_hr=rain, snow_in_per_hr=snow
    )


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, LOW),
        (24.9, LOW),
        (25, MODERATE),
        (34.9, MODERATE),
        (35, HIGH),
        (44.9, HIGH),
        (45, SEVERE),
        (54.9, SEVERE),
        (55, NO_TRAVEL),
        (80, NO_TRAVEL),
    ],
)
def test_wind_bands(mph: float, expected: RiskLevel) -> None:
    assert classify(mph, WIND_THRESHOLDS_MPH) is expected


@pytest.mark.parametrize(
    ("in_per_hr", "expected"),
    [
        (0, LOW),
        (0.09, LOW),
        (0.10, MODERATE),
        (0.24, MODERATE),
        (0.25, HIGH),
        (0.49, HIGH),
        (0.50, SEVERE),
        (1.00, SEVERE),
        (1.01, NO_TRAVEL),
    ],
)
def test_rain_bands(in_per_hr: float, expected: RiskLevel) -> None:
    assert classify(in_per_hr, RAIN_THRESHOLDS_IN_PER_HR) is expected


@pytest.mark.parametrize(
    ("in_per_hr", "expected"),
    [
        (0, LOW),
        (0.49, LOW),
        (0.5, MODERATE),
        (0.99, MODERATE),
        (1.0, HIGH),
        (1.99, HIGH),
        (2.0, SEVERE),
        (3.0, SEVERE),
        (3.01, NO_TRAVEL),
    ],
)
def test_snow_bands(in_per_hr: float, expected: RiskLevel) -> None:
    assert classify(in_per_hr, SNOW_THRESHOLDS_IN_PER_HR) is expected


@pytest.mark.parametrize(
    ("wind_level", "load_lb", "expected"),
    [
        (SEVERE, 30_000, SEVERE),
        (SEVERE, 30_001, NO_TRAVEL),
        (HIGH, 40_000, HIGH),
        (HIGH, 40_001, SEVERE),
        (MODERATE, 80_000, MODERATE),
        (LOW, 80_000, LOW),
        (NO_TRAVEL, 0, NO_TRAVEL),
    ],
)
def test_load_rules(wind_level: RiskLevel, load_lb: float, expected: RiskLevel) -> None:
    assert apply_load_rules(wind_level, load_lb) is expected


def test_high_wind_with_heavy_load_is_not_escalated_twice() -> None:
    # 40 mph is High; a 50,000 lb load makes it Severe, not No Travel.
    assessment = assess(conditions(wind=40), load_weight_lb=50_000)

    assert assessment.level is SEVERE
    assert assessment.load_adjusted


def test_gusts_drive_wind_classification() -> None:
    assessment = assess(conditions(wind=20, gust=47), load_weight_lb=10_000)

    assert assessment.hazard_levels[Hazard.WIND] is SEVERE


def test_sustained_wind_counts_when_gust_is_missing() -> None:
    assessment = assess(conditions(wind=36, gust=0), load_weight_lb=10_000)

    assert assessment.hazard_levels[Hazard.WIND] is HIGH


def test_overall_level_is_the_worst_hazard() -> None:
    assessment = assess(conditions(gust=26, rain=0.3, snow=2.5), load_weight_lb=10_000)

    assert assessment.level is SEVERE
    assert assessment.causes == (Hazard.SNOW,)
    assert not assessment.load_adjusted


def test_all_hazards_at_the_worst_level_are_reported_as_causes() -> None:
    assessment = assess(conditions(gust=36, rain=0.3), load_weight_lb=10_000)

    assert assessment.causes == (Hazard.WIND, Hazard.RAIN)


def test_calm_weather_has_no_causes() -> None:
    assessment = assess(conditions(), load_weight_lb=80_000)

    assert assessment.level is LOW
    assert assessment.causes == ()
