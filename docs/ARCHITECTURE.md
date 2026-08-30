# Architecture

## Shape

```
  NASA data services            HITS                      User
  ─────────────────────         ────────────────────      ──────────
  JPL Horizons        ──────▶  solver/     ──┐
  Small-Body Database          (hapsira)     │
  (designation only)                         ├──▶  api/    ──▶  web
                               agent/      ──┘   (FastAPI)      (one URL)
                               (Granite)
                                   ▲
                                   │
                               verify/  ──▶  judges endpoints
```

Four layers, each with a single responsibility.

**solver/** — orbital mechanics. Pulls ephemerides from JPL Horizons through
astroquery (`solver/fetch.py`), runs Lambert solves over hyperbolic targets,
grids over departure dates and flight times. The Small-Body Database is the
catalog the target designation comes from; it is not queried programmatically.
Deterministic and credential-free. Every number the system reports originates
here.

**agent/** — Granite. Calls the solver as a tool, interprets its output,
explains in plain language. Produces no figures of its own.

**verify/** — validation and evaluation modules. Imported by the test suite and
by the judges endpoints, so the same code proves the claim in CI and in a
browser.

**api/** — FastAPI. Exposes solving, explanation, and the judges endpoints.

**web/** — one URL, no build step for the user, works on a phone.

## Why this and not a GMAT plugin

Extending GMAT would place the work inside a tool that already requires
mission-design expertise to operate, leaving the accessibility gap exactly
where it was. Building on the data services instead means the layer HITS adds
is the layer the public touches.

The same reasoning drives the deployment constraint. A tool whose argument is
that existing software is inaccessible cannot itself require a clone, a
virtual environment, and an API key.

## Ordering guarantee

The solver runs first and completes before the agent is invoked. The agent
receives solver output as structured data and cannot trigger a recomputation
with different parameters. This makes the groundedness check tractable: the set
of legitimate numbers is fixed before generation begins.

## Degrade path

| Failure | Behaviour |
|---|---|
| watsonx unavailable | Solver output renders with a templated explanation. Numbers unaffected |
| Guardian unavailable | Deterministic groundedness check still runs and is still dispositive. Advisory verdict reported as unavailable |
| Horizons unreachable | Cached ephemerides for known targets serve the request, with the cache date shown |
| Host cold start | Keepalive cron pings `/health` every ten minutes to prevent sleep |

The ordering is deliberate: every failure degrades the explanation, never the
numbers.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/solve` | Raw solver output for a target and departure window |
| `/explain` | Granite interpretation of a solve, with groundedness verdict |
| `/validation` | Solver agreement against published mission-design figures |
| `/evidence` | Corpus and clustering results behind the problem statement |
| `/faithfulness` | Groundedness pass rate |
| `/health` | Liveness |

Judges endpoints return the same payloads the test suite asserts against.
