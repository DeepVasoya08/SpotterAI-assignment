"""HERE Routing v8 and Geocoding & Search v7 client.

Routes are requested in truck mode with the load's gross weight, so the provider avoids
roads the truck may not use. Each route's polyline is paired with HERE's per-span
driving time, spread across the span's vertices by distance, giving the elapsed time
at every vertex that checkpoint sampling needs.
"""

from collections.abc import Sequence
from datetime import datetime
from itertools import pairwise
from typing import Any

import flexpolyline
import httpx

from domain.geo import GeoPoint, haversine_miles
from domain.sampling import RoutePath
from integrations.errors import ProviderError
from integrations.routing import Place, RouteOption

PROVIDER = "HERE"
ROUTES_URL = "https://router.hereapi.com/v8/routes"
AUTOSUGGEST_URL = "https://autosuggest.search.hereapi.com/v1/autosuggest"
METERS_PER_MILE = 1609.344
KILOGRAMS_PER_POUND = 0.45359237
ALTERNATIVE_ROUTES = 2
# Biases suggestions towards the contiguous United States.
US_CENTER = GeoPoint(39.8283, -98.5795)


class HereClient:
    def __init__(self, api_key: str, http: httpx.Client) -> None:
        self._api_key = api_key
        self._http = http

    def search_places(self, query: str, limit: int) -> list[Place]:
        payload = self._get(
            AUTOSUGGEST_URL,
            [
                ("q", query),
                ("at", _format_point(US_CENTER)),
                ("in", "countryCode:USA"),
                ("limit", str(limit)),
            ],
        )
        # Query suggestions ("restaurants near...") have no position and are skipped.
        try:
            return [
                Place(
                    id=item["id"],
                    label=item.get("address", {}).get("label", item["title"]),
                    point=GeoPoint(item["position"]["lat"], item["position"]["lng"]),
                )
                for item in payload.get("items", [])
                if "position" in item
            ]
        except (KeyError, TypeError) as error:
            raise ProviderError(PROVIDER, "malformed place search response") from error

    def truck_routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        departure: datetime,
        gross_weight_lb: float,
        via: Sequence[GeoPoint] = (),
    ) -> list[RouteOption]:
        params: list[tuple[str, str]] = [
            ("transportMode", "truck"),
            ("origin", _format_point(origin)),
            ("destination", _format_point(destination)),
            ("departureTime", departure.isoformat(timespec="seconds")),
            ("vehicle[grossWeight]", str(round(gross_weight_lb * KILOGRAMS_PER_POUND))),
            ("return", "polyline,summary"),
            ("spans", "duration"),
            *(("via", _format_point(point)) for point in via),
        ]
        if not via:
            params.append(("alternatives", str(ALTERNATIVE_ROUTES)))

        payload = self._get(ROUTES_URL, params)
        try:
            return [_parse_route(route) for route in payload["routes"]]
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise ProviderError(PROVIDER, "malformed route response") from error

    def _get(self, url: str, params: Sequence[tuple[str, str]]) -> dict[str, Any]:
        try:
            response = self._http.get(url, params=[*params, ("apiKey", self._api_key)])
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ProviderError(PROVIDER, _error_reason(error.response)) from error
        except httpx.HTTPError as error:
            raise ProviderError(PROVIDER, "request failed") from error

        payload: dict[str, Any] = response.json()
        return payload


def _parse_route(route: dict[str, Any]) -> RouteOption:
    points: list[GeoPoint] = []
    elapsed: list[float] = []
    distance_m = 0.0
    duration_s = 0.0

    # Routes with via points come back as one section per leg; they are joined end to end.
    for section in route["sections"]:
        section_points = [
            GeoPoint(lat, lon) for lat, lon, *_ in flexpolyline.decode(section["polyline"])
        ]
        summary = section["summary"]
        section_elapsed = _vertex_elapsed_s(
            section_points, section.get("spans", []), summary["duration"]
        )

        skip_joint = 1 if points else 0
        points.extend(section_points[skip_joint:])
        elapsed.extend(duration_s + t for t in section_elapsed[skip_joint:])
        distance_m += summary["length"]
        duration_s += summary["duration"]

    return RouteOption(
        path=RoutePath(points=tuple(points), elapsed_s=tuple(elapsed)),
        distance_miles=distance_m / METERS_PER_MILE,
        duration_s=duration_s,
    )


def _vertex_elapsed_s(
    points: Sequence[GeoPoint], spans: Sequence[dict[str, Any]], total_duration_s: float
) -> list[float]:
    """Elapsed driving time at each vertex of one section.

    A span covers vertices from its ``offset`` up to the next span's offset. Without
    spans, the section's total duration is spread over the whole polyline.
    """
    last_index = len(points) - 1
    if spans:
        offsets = [span["offset"] for span in spans]
        durations = [float(span["duration"]) for span in spans]
    else:
        offsets, durations = [0], [float(total_duration_s)]
    boundaries = [*offsets, last_index]

    elapsed = [0.0] * len(points)
    clock = 0.0
    for (start, end), duration in zip(pairwise(boundaries), durations, strict=True):
        segment_miles = [haversine_miles(a, b) for a, b in pairwise(points[start : end + 1])]
        span_miles = sum(segment_miles)
        for index, miles in enumerate(segment_miles, start=start + 1):
            share = miles / span_miles if span_miles else 1 / len(segment_miles)
            clock += duration * share
            elapsed[index] = clock
    return elapsed


def _format_point(point: GeoPoint) -> str:
    return f"{point.lat:.6f},{point.lon:.6f}"


def _error_reason(response: httpx.Response) -> str:
    try:
        payload = response.json()
        reason = payload.get("title") or payload.get("error_description")
    except ValueError:
        reason = None
    return f"HTTP {response.status_code}" + (f": {reason}" if reason else "")
