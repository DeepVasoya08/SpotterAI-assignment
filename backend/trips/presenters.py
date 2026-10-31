"""JSON representations of trip plans.

Route geometry is thinned to one vertex every ``GEOMETRY_SPACING_MILES`` and written as
GeoJSON ``[lon, lat]`` pairs, which keeps responses small while staying visually exact
at any zoom level a trip-length route is viewed at.
"""

from collections.abc import Sequence
from typing import Any

from domain.geo import GeoPoint, haversine_miles
from domain.risk import RiskLevel
from integrations.routing import Place
from services.corridor_forecast import CorridorForecast
from services.trip_planner import CheckpointWeather, PlannedRoute, TripPlan

GEOMETRY_SPACING_MILES = 0.1
COORDINATE_DECIMALS = 5


def level_name(level: RiskLevel) -> str:
    return level.name.lower()


def place_to_dict(place: Place) -> dict[str, Any]:
    return {
        "id": place.id,
        "label": place.label,
        "lat": place.point.lat,
        "lon": place.point.lon,
    }


def trip_plan_to_dict(plan: TripPlan) -> dict[str, Any]:
    recommendation = plan.recommendation
    return {
        "departure_time": plan.request.departure.isoformat(),
        "load_weight_lb": plan.request.load_weight_lb,
        "sampling_interval_miles": plan.request.sampling_interval_miles,
        "recommendation": {
            "route_id": recommendation.route_id,
            "decided_by": recommendation.decided_by.value,
            "all_routes_blocked": recommendation.all_routes_blocked,
            "ranking": list(recommendation.ranking),
        },
        "routes": [_route_to_dict(route) for route in plan.routes],
    }


def _route_to_dict(route: PlannedRoute) -> dict[str, Any]:
    profile = route.profile
    return {
        "id": route.id,
        "distance_miles": route.option.distance_miles,
        "duration_s": route.option.duration_s,
        "arrival_time": route.arrival.isoformat(),
        "summary": {
            "miles_by_level": {
                level_name(level): miles for level, miles in profile.miles_by_level.items()
            },
            "average_risk": profile.average_risk,
            "max_level": level_name(max(cw.assessment.level for cw in route.checkpoints)),
        },
        "geometry": _thin_geometry(route.option.path.points),
        "checkpoints": [_checkpoint_to_dict(cw) for cw in route.checkpoints],
    }


def _checkpoint_to_dict(checkpoint_weather: CheckpointWeather) -> dict[str, Any]:
    checkpoint = checkpoint_weather.checkpoint
    conditions = checkpoint_weather.conditions
    assessment = checkpoint_weather.assessment
    return {
        "distance_miles": checkpoint.distance_miles,
        "represented_miles": checkpoint.represented_miles,
        "lat": checkpoint.point.lat,
        "lon": checkpoint.point.lon,
        "eta": checkpoint_weather.eta.isoformat(),
        "weather": {
            "wind_speed_mph": conditions.wind_speed_mph,
            "wind_gust_mph": conditions.wind_gust_mph,
            "rain_in_per_hr": conditions.rain_in_per_hr,
            "snow_in_per_hr": conditions.snow_in_per_hr,
        },
        "risk": {
            "level": level_name(assessment.level),
            "hazard_levels": {
                hazard.value: level_name(level)
                for hazard, level in assessment.hazard_levels.items()
            },
            "causes": [hazard.value for hazard in assessment.causes],
            "load_adjusted": assessment.load_adjusted,
        },
    }


def _thin_geometry(points: Sequence[GeoPoint]) -> list[list[float]]:
    kept = [points[0]]
    for point in points[1:-1]:
        if haversine_miles(kept[-1], point) >= GEOMETRY_SPACING_MILES:
            kept.append(point)
    kept.append(points[-1])
    return [
        [round(point.lon, COORDINATE_DECIMALS), round(point.lat, COORDINATE_DECIMALS)]
        for point in kept
    ]


def corridor_forecast_to_dict(forecast: CorridorForecast) -> dict[str, Any]:
    """Hourly series per cell, index 0 being departure time.

    Risk is sent as level numbers (0 = Low ... 4 = No Travel) to keep the payload small.
    """
    return {
        "start_time": forecast.start.isoformat(),
        "step_degrees": forecast.step_degrees,
        "hours": len(forecast.cells[0].levels) if forecast.cells else 0,
        "cells": [
            {
                "lat": cell.point.lat,
                "lon": cell.point.lon,
                "risk": [int(level) for level in cell.levels],
                "wind_gust_mph": [round(c.effective_wind_mph) for c in cell.conditions],
                "rain_in_per_hr": [round(c.rain_in_per_hr, 2) for c in cell.conditions],
                "snow_in_per_hr": [round(c.snow_in_per_hr, 2) for c in cell.conditions],
            }
            for cell in forecast.cells
        ],
    }
