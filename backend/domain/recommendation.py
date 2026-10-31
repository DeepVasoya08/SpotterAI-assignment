"""Route ranking.

Routes are compared on, in order:

1. No Travel miles. A route with any No Travel segment always ranks behind a route with
   none, so it is only recommended when every option is blocked.
2. Severe miles.
3. High miles.
4. Distance-weighted average risk.
5. Travel time.

Mileage and averages are rounded before comparison so floating-point noise from
summing segment lengths never decides a ranking.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from domain.risk import RiskLevel

MILES_PRECISION = 1
AVERAGE_RISK_PRECISION = 2


@dataclass(frozen=True, slots=True)
class RiskSegment:
    length_miles: float
    level: RiskLevel


@dataclass(frozen=True, slots=True)
class RouteRiskProfile:
    route_id: str
    duration_s: float
    miles_by_level: dict[RiskLevel, float]
    average_risk: float

    @classmethod
    def from_segments(
        cls, route_id: str, duration_s: float, segments: Sequence[RiskSegment]
    ) -> Self:
        miles_by_level = dict.fromkeys(RiskLevel, 0.0)
        for segment in segments:
            miles_by_level[segment.level] += segment.length_miles

        total_miles = sum(miles_by_level.values())
        weighted_risk = sum(level * miles for level, miles in miles_by_level.items())
        average_risk = weighted_risk / total_miles if total_miles else 0.0

        return cls(
            route_id=route_id,
            duration_s=duration_s,
            miles_by_level=miles_by_level,
            average_risk=average_risk,
        )

    def miles_at(self, level: RiskLevel) -> float:
        return self.miles_by_level.get(level, 0.0)

    @property
    def is_blocked(self) -> bool:
        return self.miles_at(RiskLevel.NO_TRAVEL) > 0

    def ranking_key(self) -> tuple[float, float, float, float, int]:
        return (
            round(self.miles_at(RiskLevel.NO_TRAVEL), MILES_PRECISION),
            round(self.miles_at(RiskLevel.SEVERE), MILES_PRECISION),
            round(self.miles_at(RiskLevel.HIGH), MILES_PRECISION),
            round(self.average_risk, AVERAGE_RISK_PRECISION),
            round(self.duration_s),
        )


class RankingCriterion(StrEnum):
    """The first comparison that separated the recommended route from the runner-up."""

    ONLY_ROUTE = "only_route"
    AVOIDS_NO_TRAVEL = "avoids_no_travel"
    FEWER_NO_TRAVEL_MILES = "fewer_no_travel_miles"
    FEWER_SEVERE_MILES = "fewer_severe_miles"
    FEWER_HIGH_MILES = "fewer_high_miles"
    LOWER_AVERAGE_RISK = "lower_average_risk"
    SHORTER_TRAVEL_TIME = "shorter_travel_time"
    TIED = "tied"


_CRITERIA_BY_KEY_INDEX = (
    RankingCriterion.FEWER_NO_TRAVEL_MILES,
    RankingCriterion.FEWER_SEVERE_MILES,
    RankingCriterion.FEWER_HIGH_MILES,
    RankingCriterion.LOWER_AVERAGE_RISK,
    RankingCriterion.SHORTER_TRAVEL_TIME,
)


@dataclass(frozen=True, slots=True)
class Recommendation:
    route_id: str
    decided_by: RankingCriterion
    all_routes_blocked: bool
    ranking: tuple[str, ...]


def recommend(profiles: Sequence[RouteRiskProfile]) -> Recommendation:
    if not profiles:
        raise ValueError("At least one route is required to make a recommendation.")

    # sorted() is stable, so exact ties keep the routing provider's order.
    ranked = sorted(profiles, key=RouteRiskProfile.ranking_key)
    best = ranked[0]

    return Recommendation(
        route_id=best.route_id,
        decided_by=_deciding_criterion(best, ranked[1] if len(ranked) > 1 else None),
        all_routes_blocked=all(profile.is_blocked for profile in profiles),
        ranking=tuple(profile.route_id for profile in ranked),
    )


def _deciding_criterion(
    best: RouteRiskProfile, runner_up: RouteRiskProfile | None
) -> RankingCriterion:
    if runner_up is None:
        return RankingCriterion.ONLY_ROUTE
    if runner_up.is_blocked and not best.is_blocked:
        return RankingCriterion.AVOIDS_NO_TRAVEL

    for index, (best_value, other_value) in enumerate(
        zip(best.ranking_key(), runner_up.ranking_key(), strict=True)
    ):
        if best_value != other_value:
            return _CRITERIA_BY_KEY_INDEX[index]
    return RankingCriterion.TIED
