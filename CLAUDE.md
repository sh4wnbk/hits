# CLAUDE.md

Read this first. It primes a session on what HITS is, what it refuses to do,
and how work here is judged.

## What HITS is

HITS is an accessibility layer over NASA data services that answers one
question about an interstellar object: could we send a probe to it?

Deterministic orbital mechanics computes the answer. A Granite agent
interprets it. The tool is reachable at one URL with no setup.

It is not a general mission-design environment, and not a competitor to GMAT.
It answers one question well.

## Three-question test for new components

Before building anything, it must answer yes to one of these:

1. Does it make the trajectory computation more correct?
2. Does it make the result more usable by someone without mission-design
   training?
3. Does it make a claim more verifiable by a reader?

If none, it waits. "It will be cleaner in anticipation of future features" is
not a yes.

## Layer map

```
DATA        JPL Horizons, Small-Body Database
GEOMETRY    ephemerides, state vectors, frames, epochs
SOLVER      Lambert over hyperbolic targets, grid over departure/flight time
INTERPRET   Granite agent, groundedness gate
SURFACE     API, judges endpoints, web
```

Each layer consumes the one below it. The interpretation layer never reaches
past the solver to the data.

## Non-negotiables

**Every number is computed, never generated.** The model explains solver
output. It does not produce figures. A deterministic check compares every
numeric token in an explanation against the solver's output before the
explanation is returned, and that check is dispositive. Granite Guardian is
advisory on top of it.

**The solver runs before the agent, and completes.** The agent receives
structured output and cannot trigger a recomputation with different
parameters. This is what makes the groundedness check tractable: the set of
legitimate numbers is fixed before generation begins.

**Accessibility is a design gate, not a final phase.** No clone, no virtual
environment, no API key, works on a phone. A tool whose argument is that
existing software is inaccessible cannot itself be inaccessible. Any decision
that adds a setup step for the user needs a reason that survives this.

**Failures degrade the explanation, never the numbers.** If watsonx is down,
trajectories still compute and still render.

**Report disagreement.** Where HITS differs from published mission-design
figures, say so and by how much. A validation document that only reports
agreement is marketing.

**State the fidelity limits.** HITS models patched-conic transfers. It does
not do n-body integration and does not model non-gravitational forces. Say
this wherever a number is presented as authoritative.

## Discipline

**Validate with plots before believing numbers.** A porkchop grid that looks
wrong is wrong, and this has caught something real at every layer of every
project run this way.

**No solver behaviour is believed until a test or a plot demonstrates it.**
This includes reasoning that sounds correct, whether it came from a person or
an assistant. On a prior project an assistant reasoned its way to a bug that
did not exist, and only running the tests settled it. The hazard is worse
here, because a plausible wrong delta-v is far harder to spot than a plausible
wrong diagnosis. An explanation of what the code does is a hypothesis until
executed.

**Baseline the dependencies before building on them.** Record hapsira's and
astropy's own test and lint state before writing solver code, so pre-existing
breakage is never mistaken for something HITS introduced.

**Offline and credentialed results are reported separately.** Never let a
no-credentials floor be mis-credited to the credentialed system. Judges
endpoints state which path produced each figure.

**Write the validation once.** The same module is imported by the test suite
and by the judges endpoint, so proof in CI and proof in a browser cannot
drift apart.

**No aspirational entries.** If it is not built, it is not in the README, not
in the docs, and not in the demo. Roadmap items live in `specs/roadmap.md`
under Conditional and nowhere else.

**Small branches, conventional prefixes, one concern each.** Commit history is
read by judges.

**Bob is budgeted.** 40 Bobcoins per trial account. Spend them on
correctness-critical work and review passes, not scaffolding. Record each
session in `docs/BOB_USAGE.md` as it happens, since it cannot be
reconstructed later.

## Accuracy guardrails

Facts this project has already got wrong once, or is likely to. Correct them
here rather than rediscovering them. Anyone working in this repository, human
or assistant, should treat this list as authoritative over their own recall.

- **poliastro is archived.** It pulls astropy 3.x and fails to build on
  Python 3.12. The maintained fork is hapsira, same API. Do not write install
  instructions naming poliastro.
- **TRACE is The Aerospace Corporation's, not SwRI's.** SwRI's interstellar
  intercept software is separate and unnamed publicly. Both are internal. The
  Aerospace Corporation lineage traces to a 1964 orbit determination report,
  SSD-TDR-64-159.
- **The gap is usability, not availability.** GMAT and OITS are both free and
  public. Never write that no software exists, or that these tools are
  unavailable. The claim is that no *accessible* tool exists, and it is
  narrower and defensible.
- **Granite Speech is speech-to-text only.** Input, not output. There is no
  text-to-speech in the Granite family. A spoken reply would use the browser
  SpeechSynthesis API.
- **Granite is not required by the rules.** The rules require IBM Bob as the
  primary development tool and AI as a core functional component. Granite is
  listed as recommended. It is used here because judging scores effective use
  of IBM technologies, not because it is mandatory. Do not claim it is
  required.
- **"JPL-grade" is not a claim this project has earned.** HITS runs
  patched-conic Lambert solves, not GMAT-class modelling. The tagline is
  "Expert-level intercept analysis, open to everyone." If the phrase
  "JPL-grade" is ever used, a validation comparison against published figures
  must be shown alongside it.
- **The evidence corpus is 14,293 comments from six videos**, not five, and
  not a random sample of public interest. Limits are stated in
  `docs/EVIDENCE.md` and should not be dropped when the number is quoted
  elsewhere.
- **The first clustering run failed and its output is not a result.** HDBSCAN
  directly on 384-dimensional embeddings collapsed to one cluster of 2,276
  questions. UMAP before clustering fixed it. Never cite the collapsed run.
- **Bob is 40 Bobcoins per trial account.** A new account with a different
  email yields a fresh 30-day trial, which the official challenge page
  sanctions. It is a budget, not an unlimited resource.

### Plan versus shipped

The single most likely failure mode in this repository is a document
describing something the code does not do. The specs were written before the
solver existed, so every claim in `docs/` is provisional until the
corresponding code lands.

When implementation diverges from a spec, correct the spec and record the
correction here. Do not let a planning document stand as a description of
shipped behaviour, and do not repeat a doc's claim externally without
checking the code first.

Phase 1 built and validated (initial 2025-07-13; revision completed 2026-08-27):
- solver/ package: constants, fetch, lambert, solve, grid, validate, plot
- tests/: test_baseline, test_fetch, test_lambert, test_solve, test_validation
- data/state_vectors.json: 6 committed entries (4 single states + 2 grid windows; 391 + 1044 states in grids)
- plots/c3_floor_slice.html: C3 porkchop slice, departure 2018-2032 vs duration 5-30 yr
- Validation result (revision): 41 passed, 1 skipped, 1 xfailed (matplotlib/NumPy2 pre-existing), 0 failed
- Frame gate: v_inf = 26.286 km/s vs 26.33 published (diff 0.044 km/s, PASS). Citation: Hein et al. 2019, p.553 col 1.
- C3 2027: 1331.16 km^2/s^2 vs 1400 published (diff 68.84, 4.92%, within 20% tol, PASS). Citation: p.554 col 1.
- C3 floor: 714.36 km^2/s^2 vs 703 published (diff 11.36, 1.62%, ASSERTED). Floor at 2018-06-04, TOF 30 yr. The extended-trend check on the committed oumuamua_c3_grid shows C3 dropping only 3.39 km^2/s^2 across the 30-to-44-yr span, so the curve has levelled and the duration-axis read is not mid-descent. Gap attributed to orbit-solution epoch drift (retrieval 2026-08-27 vs Lyra 2019). Citation: p.553 col 2 / Fig.1.
- Sample A: v_inf2 (eq.4) = 13.967 km/s vs 13.6 published (diff 0.367 km/s, within 2.0 tol, ASSERTED). v_arr_local = 13.716 km/s. Def. gap 0.251 km/s (hyperbolic geometry at 5.852 AU). Citation: p.554 col 2 / Fig.5.
- Sample B: v_inf2 (eq.4) = 0.642 km/s vs 0.6 published (diff 0.042 km/s, within 0.3 tol, ASSERTED). v_arr_local = 0.644 km/s. Encounter at 115.079 AU vs paper's 111.4 AU (3.7 AU orbit-solution drift). Citation: p.554 col 2 / Fig.6.
- All Lyra citations filled from Hein et al. 2019 (Acta Astronautica 161, 552-561). PDF committed to data/lyra/.
- Retrieval date for all state vectors: 2026-08-27.

Currently unbuilt, and therefore not to be described as working: the
groundedness gate, every judges endpoint, the frontend, and the deployment.

## Provenance and reproducibility

- Ephemerides are cached and committed, so validation does not depend on
  Horizons being reachable
- Horizons data updates as observations accumulate; numbers carry the date
  they were computed
- Docker is the reproducibility boundary. A judge re-running validation gets
  identical numbers, not whatever their local astropy produces
- The evidence corpus, cluster report, and mining scripts stay in `/data`.
  Claims in the problem statement must resolve to files that exist

## Environment

- WSL2, `~/projects/hits`, Python 3.12.3 (`.venv/pyvenv.cfg` confirmed; stated 3.11 in error, corrected 2025-07-13)
- poliastro is archived and will not install on 3.12. hapsira is the
  drop-in replacement
- Design decisions in chat, mechanical implementation delegated
- Install-test the scientific stack on the host in week one

## Writing rules

- No em dashes. Use commas, colons, parentheses, or separate sentences
- Prose carries an argument forward in connected paragraphs. Bullets and bold
  labels are for material executed or verified line by line
- Stick to the data. If something is not in the source, leave it out and flag
  the gap rather than filling it in
