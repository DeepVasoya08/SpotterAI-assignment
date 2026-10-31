"""Map domain and provider failures to API responses."""

import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from domain.forecast import ForecastUnavailableError
from integrations.errors import ProviderError
from services.trip_planner import NoRouteFoundError

logger = logging.getLogger(__name__)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, ProviderError):
        logger.warning("Upstream provider failed: %s", exc)
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            f"{exc.provider} is unavailable right now. Please try again shortly.",
        )
    if isinstance(exc, NoRouteFoundError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No truck route was found between these places.",
        )
    if isinstance(exc, ForecastUnavailableError):
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The weather forecast does not cover this trip. Choose an earlier departure.",
        )
    return drf_exception_handler(exc, context)


def _error(status_code: int, detail: str) -> Response:
    return Response({"detail": detail}, status=status_code)
