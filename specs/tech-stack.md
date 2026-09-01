# Tech Stack

Every entry states what it does and why it is here. Anything without a real
job is listed under Rejected rather than kept for appearances.

## Orbital mechanics

| Component | Role |
|---|---|
| hapsira | Lambert solvers over hyperbolic orbits. Maintained fork of poliastro, which is archived and will not install on modern Python |
| astropy | Time systems, units, coordinate frames |
| astroquery | Client for JPL Horizons |
| numpy | Grid computation over departure dates and flight times |

Note: poliastro 0.12 pulls astropy 3.x and fails to build on Python 3.12.
hapsira is a drop-in replacement with the same API.

## Space data services

The layer HITS is built on. Both are NASA services, and HITS extends them
rather than duplicating them: the ephemerides are theirs, the trajectory
analysis over those ephemerides is what HITS adds.

| Source | Role | Where it enters the code |
|---|---|---|
| JPL Horizons | Ephemerides and state vectors for target objects and departure bodies, heliocentric ECLIPJ2000, queried through astroquery | `solver/fetch.py` (`_query_horizons`, `fetch_state_vector`, `fetch_window`) |
| JPL Small-Body Database | The catalog the target designation is taken from. 1I/'Oumuamua resolves to the Horizons id `1I`, which pins the orbit solution | Not called programmatically. The designation is a constant in `solver/fetch.py` (`OUMUAMUA_ID`) |

Retrieved states are committed to `data/state_vectors.json` with their
retrieval date, so validation runs offline and does not depend on Horizons
being reachable. Every fetch converts AU and AU/day to km and km/s at the
boundary, per `docs/CONVENTIONS.md`.

## IBM components

| Component | Role | Verifiable at |
|---|---|---|
| IBM Bob | Primary development tool | `BOB_USAGE.md` |
| Granite (via watsonx) | Reasoning layer: interprets solver output under the groundedness gate | `agent/granite.py`, live 2026-08-30 |

Granite Guardian and Granite embeddings were both planned and neither is
built. What that means in detail, and what the shipped evidence pipeline
actually embeds with, is in `docs/IBM_STACK.md` under Not wired.

Granite is not literally required by the rules, which mandate only Bob plus AI
as a core component. It is here because judging scores effective use of IBM
technologies, and because the reasoning layer needs a model regardless.

## Application

| Component | Role |
|---|---|
| FastAPI | The service. `/health`, `/objects`, `/explain/{key}`, `/evidence/{eid}`, `/gate/demo/{key}`, `/chips`, and the page at `/` |
| Python 3.12 | Runtime. 3.12.3 on the development host and pinned to the same on the deployment. poliastro is what fails on 3.12, and hapsira replaced it |
| GitHub Actions | CI gates the full suite on every push. It also carries a keepalive cron, which does not work; see Hosting |

## Frontend

No framework and no build step. `web/index.html` is one self-contained
document: its stylesheet, its script and its two photographs are inline, so the
page a reader gets is the file in the repository, byte for byte. FastAPI serves
it with `FileResponse`. `web/gate.html` is the same shape for the readable view
of the number check.

That is the accessibility non-negotiable applied to the page's own delivery.
One URL, nothing to install, works on a phone. Its only outbound request is a
Google Fonts stylesheet for IBM Plex, behind a real fallback stack.

It carries a day and night toggle, four text-size steps, a human-readable
noscript block naming the endpoints a reader can reach without JavaScript, and
Open Graph tags so the link renders as a card when pasted.

No number is written into it. Object answers come from `/explain/{key}`,
evidence answers from `/evidence/{eid}`, and the accepted and rejected figures
in the gate exhibit from `/gate/demo/oumuamua`.
`tests/test_serve_imports.py::test_index_states_no_number` fails if a solver
figure is ever typed in.

## Hosting

Render, free plan, from `render.yaml` as a Blueprint. Live at
`https://hits-f3s4.onrender.com`, deploying from `main`.

The plan chosen was the one this document set out to avoid, and the reason it
became viable is worth stating, because it inverts the note that used to be
here. The old worry was that compiled astropy and numpy dependencies are where
hosted environments fail, so the scientific stack had to be install-tested on
the host early. The deployment now never installs it. `requirements-serve.txt`
names fastapi, uvicorn and requests and nothing else: the solver ran at build
time and its output is committed to `data/manifests/`, so the web process reads
json. That is what makes a free instance viable at all, and
`tests/test_serve_imports.py` fails if a handler ever reaches for the solver at
request time.

No `WATSONX_*` value is set on the deployment. With the credentials absent
`agent/explain.py` serves the deterministic floor and reports
`served_by=deterministic_floor`, which is the path that reproduces with no
account and no network.

The cold start the free plan was avoided for is real and was not designed away.
A free instance sleeps after inactivity and the next request pays it: measured
at 22.98 seconds on `/health`. The keepalive Action was meant to prevent that
and does not fire often enough to, one run where a ten-minute cron predicts
about thirty-nine, which is recorded in the workflow's own comment. An external
pinger is what the job needs, and it is not in this repository.

A move to AWS or GCP would need a container, and there is no Dockerfile here.

## Rejected

| Considered | Why not |
|---|---|
| Extending GMAT as a plugin | The work would live inside a tool that already requires expertise, leaving the accessibility gap unsolved |
| poliastro | Archived 2023, incompatible with current Python |
| Docling | Heavy dependency chain for a one-time PDF ingest. The Lyra and OITS papers are parsed once and committed as text |
| MLflow / Weights & Biases | Experiment tracking with no experiments. Revisit only if the surrogate model is built |
| AWS / GCP | Setup surface with no judge-visible benefit. The cold-start argument that was also made here did not survive contact with the free Render plan, which has one |
| Docker | Listed here as a reproducibility boundary until 2026-08-31, when it was noticed that no Dockerfile was ever written. The deployment is `runtime: python` with pip, and reproducibility rests on pinned versions plus committed ephemerides and manifests instead |
| Replit Core | The alternative host. Render was chosen and shipped; carrying a second one in the stack was a decision the document had not made |
| Continue plus local Granite via Ollama | A second AI coding assistant dilutes the Bob usage story, and the hardware would make it slow |
| Granite Speech | Speech-to-text only, input rather than output. Voice reply would be the browser SpeechSynthesis API, and is a flourish behind the solver |
| Context Forge, Granite Nano | Real components, no job in this architecture |
| "Artificial versus natural" classification | Not defensible science. Also feeds the conspiracy cluster in the corpus rather than the legitimate questions |
