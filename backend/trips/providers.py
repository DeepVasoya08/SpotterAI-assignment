"""Construction of the external service clients used by the views."""

from functools import cache

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from integrations.here import HereClient
from integrations.open_meteo import OpenMeteoClient
from services.trip_planner import TripPlanner

REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
CONNECT_RETRIES = 2


@cache
def http_client() -> httpx.Client:
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        transport=httpx.HTTPTransport(retries=CONNECT_RETRIES),
    )


def here_client() -> HereClient:
    if not settings.HERE_API_KEY:
        raise ImproperlyConfigured("HERE_API_KEY is not set.")
    return HereClient(settings.HERE_API_KEY, http_client())


def trip_planner() -> TripPlanner:
    return TripPlanner(routing=here_client(), weather=OpenMeteoClient(http_client()))
