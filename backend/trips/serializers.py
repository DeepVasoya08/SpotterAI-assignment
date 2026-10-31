from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from domain.geo import GeoPoint
from services.trip_planner import TripRequest

SAMPLING_INTERVALS_MILES = (10, 25, 50)
MAX_LOAD_WEIGHT_LB = 80_000
# Departures must leave room for the trip itself inside the forecast horizon.
MAX_DEPARTURE_AHEAD = timedelta(days=7)
DEPARTURE_GRACE = timedelta(minutes=30)
MAX_PATHS = 3
MAX_PATH_POINTS = 1_000


class PointSerializer(serializers.Serializer[GeoPoint]):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class PlaceSearchSerializer(serializers.Serializer[dict[str, Any]]):
    q = serializers.CharField(min_length=3, max_length=200, trim_whitespace=True)


def validate_departure(value: datetime) -> None:
    now = timezone.now()
    if value < now - DEPARTURE_GRACE:
        raise serializers.ValidationError("Departure time cannot be in the past.")
    if value > now + MAX_DEPARTURE_AHEAD:
        raise serializers.ValidationError("Departure must be within the next 7 days.")


class TripRequestSerializer(serializers.Serializer[TripRequest]):
    origin = PointSerializer()
    destination = PointSerializer()
    departure_time = serializers.DateTimeField(validators=[validate_departure])
    load_weight_lb = serializers.FloatField(min_value=1, max_value=MAX_LOAD_WEIGHT_LB)
    sampling_interval_miles = serializers.ChoiceField(choices=SAMPLING_INTERVALS_MILES)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["origin"] == attrs["destination"]:
            raise serializers.ValidationError("Origin and destination must be different.")
        return attrs

    def to_trip_request(self) -> TripRequest:
        data = self.validated_data
        return TripRequest(
            origin=GeoPoint(**data["origin"]),
            destination=GeoPoint(**data["destination"]),
            departure=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            sampling_interval_miles=data["sampling_interval_miles"],
        )


class CorridorForecastRequestSerializer(serializers.Serializer[dict[str, Any]]):
    """The routes' checkpoints describe the corridor; full geometry is not needed."""

    paths = serializers.ListField(
        child=serializers.ListField(
            child=PointSerializer(), min_length=2, max_length=MAX_PATH_POINTS
        ),
        min_length=1,
        max_length=MAX_PATHS,
    )
    departure_time = serializers.DateTimeField(validators=[validate_departure])
    load_weight_lb = serializers.FloatField(min_value=1, max_value=MAX_LOAD_WEIGHT_LB)

    def paths_as_points(self) -> list[list[GeoPoint]]:
        return [[GeoPoint(**point) for point in path] for path in self.validated_data["paths"]]
