from django.urls import path

from trips import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("places/", views.PlaceSearchView.as_view(), name="place-search"),
    path("trips/plan/", views.TripPlanView.as_view(), name="trip-plan"),
    path(
        "trips/corridor-forecast/",
        views.CorridorForecastView.as_view(),
        name="corridor-forecast",
    ),
]
