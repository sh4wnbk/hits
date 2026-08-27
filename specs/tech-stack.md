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

## Data sources

| Source | Role |
|---|---|
| JPL Horizons | Ephemerides and state vectors for target objects and departure bodies |
| JPL Small-Body Database | Object catalog and orbital elements |

Both are NASA services. HITS extends them rather than duplicating them.

## IBM components

| Component | Role | Verifiable at |
|---|---|---|
| IBM Bob | Primary development tool | `docs/BOB_USAGE.md` |
| Granite (via watsonx) | Reasoning layer: orchestrates the solver as a tool, interprets results | `/explain` |
| Granite Guardian | Advisory groundedness check on generated explanations | `/faithfulness` |
| Granite embeddings | Sentence embeddings in the evidence pipeline, replacing MiniLM | `/evidence` |

Granite is not literally required by the rules, which mandate only Bob plus AI
as a core component. It is here because judging scores effective use of IBM
technologies, and because the reasoning layer needs a model regardless.

## Application

| Component | Role |
|---|---|
| FastAPI | Solver API and judges endpoints |
| Python 3.11 | Runtime. 3.12 causes dependency friction with the scientific stack |
| Docker | Reproducible environment, so a judge re-running validation gets identical numbers |
| GitHub Actions | CI gates plus a keepalive cron against the host's sleep timer |

## Frontend

Decided at build time, constrained by the accessibility non-negotiable: one
URL, no build step for the user, works on a phone. Ships with a human-readable
noscript block and Open Graph tags so the link renders as a card when pasted.

## Hosting

Replit Core (annual, available) or Render. Free-tier cloud is avoided not on
cost but on cold starts and configuration surface, neither of which a judge
will wait through. Containerization keeps a move to AWS or GCP open, and
`docs/DEPLOY.md` documents that path without spending August on it.

Install-test the scientific stack on the chosen host in week one. Compiled
astropy and numpy dependencies are where hosted environments tend to fail, and
discovering that in week four is fatal.

## Rejected

| Considered | Why not |
|---|---|
| Extending GMAT as a plugin | The work would live inside a tool that already requires expertise, leaving the accessibility gap unsolved |
| poliastro | Archived 2023, incompatible with current Python |
| Docling | Heavy dependency chain for a one-time PDF ingest. The Lyra and OITS papers are parsed once and committed as text |
| MLflow / Weights & Biases | Experiment tracking with no experiments. Revisit only if the surrogate model is built |
| AWS / GCP | Cold starts and setup surface with no judge-visible benefit |
| Continue plus local Granite via Ollama | A second AI coding assistant dilutes the Bob usage story, and the hardware would make it slow |
| Granite Speech | Speech-to-text only, input rather than output. Voice reply would be the browser SpeechSynthesis API, and is a flourish behind the solver |
| Context Forge, Granite Nano | Real components, no job in this architecture |
| "Artificial versus natural" classification | Not defensible science. Also feeds the conspiracy cluster in the corpus rather than the legitimate questions |
