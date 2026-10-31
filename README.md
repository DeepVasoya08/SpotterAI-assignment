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

```
backend/
  domain/        Pure logic: risk rules, checkpoint sampling, forecasts, ranking
  integrations/  HERE (routing, place search) and Open-Meteo (weather) clients
  services/      Trip planning: route options, weather lookup, recommendation
  trips/         Django REST API: validation, views, JSON presentation
  config/        Django settings and URLs
frontend/        React single-page app
```

Dependencies point inwards: `trips` → `services` → `integrations` → `domain`. The
domain has no framework or network code, so the rules are tested directly.

### Planning a trip

1. HERE returns truck routes for the gross weight, with two alternatives. If fewer than
   three distinct routes come back, extra candidates are forced through via points to
   either side of the direct line, and any that mostly share road with a chosen route
   are dropped.
2. Each route is sampled at the chosen interval, and every checkpoint gets an
   arrival time from HERE's per-span driving times.
3. Checkpoints within about a mile of each other share one forecast. All forecasts are
   fetched from Open-Meteo in small concurrent batches, typically in well under a second.
4. Each checkpoint is classified at its arrival time, routes are summarised, and the
   recommendation is made.

### Corridor heatmap

Once routes are shown, the app requests a corridor forecast separately, so the routes
appear without waiting for it.

- The corridor is every point within 30 miles of any route. It is covered by a grid of
  cells on a fixed global lattice. The lattice spacing (0.1° to 2°) is chosen per trip
  so the corridor stays under 300 cells: short trips get a fine grid, cross-country
  trips a coarse one.
- Each cell gets wind, rain, snow and load-adjusted risk for departure + 0…48 hours,
  using the same rules as the checkpoints.
- The map draws every cell as a square coloured by its risk band. There is a layer
  for overall risk and one each for wind, rain and snow, all coloured by the same
  bands. I chose squares over a blurred density heatmap: each square shows exactly one
  forecast and its band, and a blur would suggest detail that isn't in the data.
- All 49 hours ship in one response (about 190 kB, 16 kB gzipped, for Chicago to Denver). The slider
  and the play button only change the layer's paint expression, so moving through
  hours never refetches or re-uploads data.
- A truck marker shows where the selected route's truck will be at the chosen hour.
- Cell forecasts are cached for 30 minutes, so reopening a plan does not use up the
  weather API's daily quota again.

### API

| Method | Path               | Purpose                                         |
| ------ | ------------------ | ----------------------------------------------- |
| GET    | `/api/health/`     | Liveness check                                  |
| GET    | `/api/places/?q=`  | US place suggestions (cached for a day)         |
| POST   | `/api/trips/plan/` | Routes, checkpoints, risk and a recommendation  |
| POST   | `/api/trips/corridor-forecast/` | Hourly risk grid around the routes |

`POST /api/trips/plan/` takes:

```json
{
  "origin": { "lat": 41.8781, "lon": -87.6298 },
  "destination": { "lat": 39.7392, "lon": -104.9903 },
  "departure_time": "2026-11-01T14:00:00Z",
  "load_weight_lb": 42000,
  "sampling_interval_miles": 25
}
```

The departure must be within the next 7 days so the whole trip fits in the forecast.
Upstream failures return `502`. A missing route or forecast returns `422`. Requests
are rate-limited per client to protect the third-party API quotas.

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

The API runs on [Render](https://render.com) and the React app on
[Vercel](https://vercel.com). The page is served from Vercel's CDN, so it loads
instantly even while the API wakes up.

### API on Render

`render.yaml` defines the service.

1. In Render, choose **New → Blueprint** and select this repository.
2. When prompted, set:
   - `HERE_API_KEY`: the HERE REST API key.
   - `CORS_ALLOWED_ORIGINS`: the Vercel URL, for example `https://truck-routing.vercel.app`.
3. Render installs dependencies with `uv`, generates `DJANGO_SECRET_KEY`, and runs
   gunicorn. It checks `/api/health/` before switching traffic.

In production the API redirects HTTP to HTTPS, sends HSTS, accepts only its Render
hostname, and allows cross-origin requests only from `CORS_ALLOWED_ORIGINS`. It uses
one gunicorn process with 8 threads, so the in-memory cache and rate limits are shared
and the I/O-bound calls to HERE and Open-Meteo overlap.

### Web app on Vercel

1. Import the repository in Vercel and set **Root Directory** to `frontend`.
   `frontend/vercel.json` provides the build settings.
2. Add the environment variable `VITE_API_BASE_URL` with the Render URL, for example
   `https://truck-routing-api.onrender.com`.
3. Deploy, then put the Vercel URL into the API's `CORS_ALLOWED_ORIGINS`.

Render's free tier sleeps after 15 idle minutes, and the first request then takes up to
a minute. The page pings `/api/health/` as soon as it opens, so the API is usually
awake by the time a trip is submitted.
