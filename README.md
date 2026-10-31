# Weather-Aware Truck Routing

A React + Django web app that helps a truck driver pick the safest route between two
places, based on the weather forecast along each route, the truck's load weight and the
travel time.

> Status: in development. Sections marked _TBD_ are filled in as features land.

## Features

- Three route options between an origin and a destination
- Weather sampled every 10, 25 or 50 miles at the truck's estimated arrival time
- Risk classification per checkpoint using the wind, rain, snow and load rules
- A recommended route, with the reason it was chosen
- Map of all routes, checkpoints, risk levels, ETAs and route summaries
- Weather heatmap along the trip corridor with a 0–48 hour forecast slider

## Tech stack

| Layer    | Choice                                              |
| -------- | --------------------------------------------------- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Map      | MapLibre GL via react-map-gl, OpenFreeMap basemap   |
| Backend  | Django, Django REST Framework, httpx                |
| Routing  | HERE Routing API (truck mode) and HERE Geocoding    |
| Weather  | Open-Meteo forecast API                             |

## Getting started

### Prerequisites

- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Node.js 22 and [pnpm](https://pnpm.io/)
- A HERE API key

### Backend

```bash
cd backend
cp .env.example .env   # then set HERE_API_KEY
uv sync
uv run --env-file .env python manage.py runserver
```

The API runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The app runs on `http://localhost:5173` and proxies `/api` requests to the backend.

## Quality checks

```bash
# backend
uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest

# frontend
pnpm format:check && pnpm lint && pnpm typecheck && pnpm test
```

The same checks run in GitHub Actions on every push and pull request.

## Architecture

_TBD_

## Risk rules and assumptions

The rules live in `backend/domain/` as plain Python with no framework dependencies.

### Checkpoint risk

Each checkpoint is classified per hazard, and its overall level is the worst of the three.

| Condition | Low      | Moderate  | High      | Severe    | No Travel |
| --------- | -------- | --------- | --------- | --------- | --------- |
| Wind      | <25 mph  | 25–34     | 35–44     | 45–54     | ≥55 mph   |
| Rain      | <0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | >1.00  |
| Snow      | <0.5 in/hr  | 0.5–1.0   | 1.0–2.0   | 2.0–3.0   | >3.0   |

Load rules escalate the wind level: 45–54 mph with more than 30,000 lb is No Travel, and
35–44 mph with more than 40,000 lb is Severe.

Interpretations where the brief leaves room:

- **Wind uses gusts.** Classification uses the higher of sustained wind and gusts, since
  gusts are what push a high-sided trailer. Both values are shown in the UI.
- **Band edges.** Each band includes its lower bound (25 mph is Moderate, 0.25 in/hr is
  High), so non-integer values like 34.6 mph fall in a well-defined band. No Travel for
  rain and snow is strictly greater than the Severe ceiling, as written.
- **Load rules escalate once.** A 40 mph gust with 50,000 lb becomes Severe, not No Travel.
- **Load weight** is gross vehicle weight in pounds.

### Checkpoints and arrival times

- The driver picks a sampling interval of 10, 25 or 50 miles.
- Checkpoints are placed at that interval from the origin, plus one at the destination.
- Each checkpoint's arrival time is departure time plus the routing provider's driving
  time to that point, interpolated between route vertices. It includes traffic but not
  rest breaks.
- Each checkpoint stands for the road halfway to its neighbours. Those stretches add up
  to the route length, and they are the miles counted per risk level.

### Route recommendation

Routes are ranked by, in order:

1. No Travel miles. Any route with a No Travel segment ranks behind every route without
   one, so it is only recommended when all options are blocked, and the UI then warns
   the driver not to depart.
2. Severe miles
3. High miles
4. Distance-weighted average risk (Low = 0 … No Travel = 4)
5. Travel time

Miles are compared at 0.1 mile precision and average risk at 0.01, so floating-point
noise never decides a ranking. The API reports which of these criteria separated the
recommended route from the runner-up.

The order is applied strictly, as the brief lists it. One consequence: a route with a
short Moderate stretch loses to a clear route even when the clear route is hours longer.
The UI explains each recommendation in those terms ("Equal Severe and High exposure,
with lower overall risk than Route B") so the driver can see the trade-off.

## Deployment

_TBD_
