import pytest

from domain.recommendation import (
    RankingCriterion,
    RiskSegment,
    RouteRiskProfile,
    recommend,
)
from domain.risk import RiskLevel

HOUR = 3600.0


def route(
    route_id: str,
    duration_h: float = 10,
    low: float = 0,
    moderate: float = 0,
    high: float = 0,
    severe: float = 0,
    no_travel: float = 0,
) -> RouteRiskProfile:
    segments = [
        RiskSegment(miles, level)
        for level, miles in (
            (RiskLevel.LOW, low),
            (RiskLevel.MODERATE, moderate),
            (RiskLevel.HIGH, high),
            (RiskLevel.SEVERE, severe),
            (RiskLevel.NO_TRAVEL, no_travel),
        )
        if miles
    ]
    return RouteRiskProfile.from_segments(route_id, duration_h * HOUR, segments)


class TestRouteRiskProfile:
    def test_sums_miles_per_level(self) -> None:
        profile = RouteRiskProfile.from_segments(
            "a",
            HOUR,
            [
                RiskSegment(10, RiskLevel.LOW),
                RiskSegment(25, RiskLevel.HIGH),
                RiskSegment(15, RiskLevel.LOW),
            ],
        )

        assert profile.miles_at(RiskLevel.LOW) == 25
        assert profile.miles_at(RiskLevel.HIGH) == 25
        assert profile.miles_at(RiskLevel.SEVERE) == 0

    def test_average_risk_is_weighted_by_distance(self) -> None:
        profile = route("a", low=75, severe=25)

        assert profile.average_risk == pytest.approx(0.75)

    def test_route_without_segments_has_zero_average_risk(self) -> None:
        assert route("a").average_risk == 0


class TestRecommend:
    def test_fewest_severe_miles_wins_over_shorter_time(self) -> None:
        result = recommend(
            [route("fast", duration_h=8, severe=10), route("slow", duration_h=12, high=50)]
        )

        assert result.route_id == "slow"
        assert result.decided_by is RankingCriterion.FEWER_SEVERE_MILES

    def test_fewest_high_miles_breaks_severe_tie(self) -> None:
        result = recommend([route("a", severe=5, high=30), route("b", severe=5, high=10)])

        assert result.route_id == "b"
        assert result.decided_by is RankingCriterion.FEWER_HIGH_MILES

    def test_average_risk_breaks_high_tie(self) -> None:
        result = recommend([route("a", low=50, moderate=50), route("b", low=90, moderate=10)])

        assert result.route_id == "b"
        assert result.decided_by is RankingCriterion.LOWER_AVERAGE_RISK

    def test_travel_time_breaks_risk_tie(self) -> None:
        result = recommend([route("a", duration_h=11, low=100), route("b", duration_h=9, low=100)])

        assert result.route_id == "b"
        assert result.decided_by is RankingCriterion.SHORTER_TRAVEL_TIME

    def test_route_with_no_travel_segment_is_never_preferred_over_clear_route(self) -> None:
        result = recommend([route("blocked", no_travel=5), route("clear", severe=200)])

        assert result.route_id == "clear"
        assert result.decided_by is RankingCriterion.AVOIDS_NO_TRAVEL
        assert not result.all_routes_blocked

    def test_fewest_no_travel_miles_wins_when_all_routes_are_blocked(self) -> None:
        result = recommend([route("a", no_travel=30), route("b", no_travel=10, severe=50)])

        assert result.route_id == "b"
        assert result.decided_by is RankingCriterion.FEWER_NO_TRAVEL_MILES
        assert result.all_routes_blocked

    def test_floating_point_noise_does_not_decide_ranking(self) -> None:
        noisy = RouteRiskProfile.from_segments(
            "noisy", 9 * HOUR, [RiskSegment(0.1, RiskLevel.HIGH)] * 3
        )
        exact = RouteRiskProfile.from_segments(
            "exact", 10 * HOUR, [RiskSegment(0.3, RiskLevel.HIGH)]
        )

        result = recommend([exact, noisy])

        assert result.route_id == "noisy"
        assert result.decided_by is RankingCriterion.SHORTER_TRAVEL_TIME

    def test_identical_routes_keep_provider_order(self) -> None:
        result = recommend([route("first", low=100), route("second", low=100)])

        assert result.route_id == "first"
        assert result.decided_by is RankingCriterion.TIED

    def test_single_route(self) -> None:
        result = recommend([route("only", severe=10)])

        assert result.route_id == "only"
        assert result.decided_by is RankingCriterion.ONLY_ROUTE

    def test_ranking_lists_every_route_best_first(self) -> None:
        result = recommend(
            [route("worst", no_travel=1), route("best", low=10), route("middle", high=10)]
        )

        assert result.ranking == ("best", "middle", "worst")

    def test_requires_at_least_one_route(self) -> None:
        with pytest.raises(ValueError, match="At least one route"):
            recommend([])
