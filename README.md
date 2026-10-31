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
| Frontend | React, TypeScript, Vite, Tailwind CSS               |
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

_TBD_

## Deployment

_TBD_
