# Mission

## What HITS is

HITS (Hyperbolic Intercept & Trajectory Solver) answers one question about an
interstellar object: could we send a probe to it?

It takes a target from NASA's small-body catalogs, computes real intercept
trajectories with Lambert solvers over hyperbolic orbits, and explains the
result in plain language. Deterministic orbital mechanics produces every
number. An IBM Granite agent orchestrates the analysis and interprets it.

**Demo line:** Can we catch it?
**Tagline:** Expert-level intercept analysis, open to everyone.

## Who it is for

Students, educators, journalists, and the curious public.

Not researchers. Researchers already have GMAT and the training to run it.
The gap is not that the computation is impossible; it is that no one without
mission-design expertise can perform it.

## Why this problem

Measured, not assumed. In July 2026 we collected 19,122 YouTube comments from
six NASA Jet Propulsion Laboratory videos, extracted the questions, and grouped
them with density-based clustering. Two technical themes dominated:

| Theme | Questions |
|---|---|
| Travel time and mission feasibility | ~170 |
| Interstellar objects and intercept missions | ~85 |

View counts point the same way. Across 30 sampled recent NASA JPL uploads,
views ranged from 4,000 to 60,000. The 3I/ATLAS explainer, posted in the same
period, recorded 511,000. The same pattern appears on other space channels.

Full method, raw corpora, and cluster report: `docs/EVIDENCE.md` and `/data`.

## Why no tool answers it

Software that computes intercept trajectories exists, and has since 1964.
None of it is usable by the audience above.

| Tool | Status | Barrier |
|---|---|---|
| GMAT (NASA) | Free, open source | Mission-design expertise required |
| OITS (Project Lyra) | Open source | Orbital mechanics knowledge plus code setup |
| OTIS (NASA) | Restricted | Distribution limited to domestic United States use |
| TRACE (The Aerospace Corporation) | Internal | Never publicly released |

JPL's NEO Deflection App proves public trajectory tools work, but covers
asteroid deflection only, not interstellar intercepts.

## What HITS is not

- Not a claim that no software can do this. The claim is that no *accessible*
  tool does.
- Not a classifier of natural versus artificial objects. That question is
  answered by observational data, not by inference over orbital elements, and
  a tool that pretends otherwise would be dishonest.
- Not a replacement for GMAT. HITS answers one question well rather than many
  questions generally.
- Not a reinvention. HITS is an accessibility layer over NASA data services.

## Non-negotiables

1. **Every number is computed, never generated.** The language model explains
   solver output. It does not produce figures. A groundedness gate enforces
   this.
2. **The tool is reachable in one click.** No clone, no virtual environment,
   no API key, works on a phone. A tool that criticizes inaccessible software
   while being inaccessible has argued against itself.
3. **Claims are verifiable by the reader.** Accuracy is stated as a number
   against published mission-design literature and exposed at an endpoint
   anyone can run.
4. **The numbers survive the agent failing.** If the language model is
   unavailable, trajectories still compute and still render.
