from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips import providers
from trips.presenters import corridor_forecast_to_dict, place_to_dict, trip_plan_to_dict
from trips.serializers import (
    CorridorForecastRequestSerializer,
    PlaceSearchSerializer,
    TripRequestSerializer,
)

PLACE_SUGGESTION_LIMIT = 5
PLACE_CACHE_SECONDS = 24 * 60 * 60


@api_view(["GET"])
def health(request: Request) -> Response:
    return Response({"status": "ok"})


class PlaceSearchView(APIView):
    throttle_scope = "places"

    def get(self, request: Request) -> Response:
        serializer = PlaceSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        query: str = serializer.validated_data["q"]

        cache_key = f"places:{query.casefold()}"
        places = cache.get(cache_key)
        if places is None:
            results = providers.here_client().search_places(query, PLACE_SUGGESTION_LIMIT)
            places = [place_to_dict(place) for place in results]
            cache.set(cache_key, places, PLACE_CACHE_SECONDS)
        return Response({"results": places})


class TripPlanView(APIView):
    throttle_scope = "trip_plan"

    def post(self, request: Request) -> Response:
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = providers.trip_planner().plan(serializer.to_trip_request())
        return Response(trip_plan_to_dict(plan))


class CorridorForecastView(APIView):
    throttle_scope = "corridor_forecast"

    def post(self, request: Request) -> Response:
        serializer = CorridorForecastRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        forecast = providers.corridor_forecaster().forecast(
            paths=serializer.paths_as_points(),
            departure=serializer.validated_data["departure_time"],
            load_weight_lb=serializer.validated_data["load_weight_lb"],
        )
        return Response(corridor_forecast_to_dict(forecast))
