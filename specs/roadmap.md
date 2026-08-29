# Roadmap

Deadline: 31 August 2026, 11:59 PM ET.

Ordered by dependency. Each phase has an exit condition, because a phase that
cannot be shown to be finished will absorb the whole month.

## Phase 0 — Foundation

- Python 3.11 virtual environment (done: `~/projects/hits`)
- hapsira, astropy, astroquery, numpy installed and importing (done)
- Repository initialised, pushed public, topics tagged `ibm-skillsbuild` and
  `ibm-bob`
- `/data` populated with the corpora, cluster report, and mining scripts, so
  the evidence claims in the problem statement resolve to real files
- `channel_views.csv` recorded from the collected view counts

**Exit:** repository is public and every claim in `specs/mission.md` points at
a file that exists.

## Phase 1 — Solver core

The make-or-break phase. Everything above it assumes these numbers are right.

- Pull target state vectors from JPL Horizons via astroquery
- Pull departure-body state vectors over a date range
- Lambert solve between them, returning departure delta-v, arrival velocity,
  and flight time
- Handle the hyperbolic case explicitly rather than assuming closed orbits
- Validation suite reproducing Project Lyra's published 'Oumuamua figures
  within a stated tolerance

**Exit:** validation passes with a printed agreement figure. That number is the
headline claim of the submission.

**This is the highest-value Bob spend.** Correctness matters most here, and a
Bob review pass over the solver earns a concrete line in `BOB_USAGE.md`.

**Absorbed from the old Phase 2**, and delivered here: gridding the solver over
departure dates and flight times, and porkchop rendering. `solver/grid.py` and
`plots/c3_floor_slice.html` are the result. A trajectory plot for a selected
solution was in that phase and is not built.

## Phase 2 — Granite layer and the groundedness gate

The numbering originally put grid and visualization at Phase 2 and the Granite
layer at Phase 3. The work did not run that way. Gridding and the C3 porkchop
landed inside Phase 1 alongside the solver, and the phase every commit, every
BOB_USAGE.md entry and CLAUDE.md itself calls Phase 2 is the gate. There is
therefore no Phase 3: the old Phase 3 is this one, and the old Phase 2 is
folded into Phase 1 below. Phases 4 and 5 keep their numbers, because
renumbering them would break references for the sake of tidiness.

The headings now match what was built. A roadmap that disagrees with the commit
log is not a plan, it is a second version of events.

- Solver exposed as a tool the agent calls
- Explanations generated from solver output only
- Deterministic groundedness gate: every numeric token in an explanation must
  appear in the solver's output. Set comparison, dispositive
- Granite Guardian as an advisory second layer
- Degrade path: if watsonx is unavailable, numbers still render with a
  templated explanation

**Exit:** the agent explains a real result, and the groundedness gate blocks a
deliberately ungrounded one.

**Built so far:** the manifest, the extraction rule, and the gate's membership
and attribution checks, against a 33-case reject corpus and a 14-case accept
corpus. The Granite agent layer, Guardian, and the degrade path are not built.

## Phase 4 — Proof surface

- `/validation` — solver agreement against published figures
- `/solve` — raw solver output for a given target
- `/evidence` — corpus and clustering results behind the problem statement
- `/faithfulness` — groundedness pass rate
- `/health` — liveness
- Judges page linking each judging criterion to the endpoint that demonstrates it
- CI: tests, repo hygiene (fail if a `.env` is ever tracked), no `|| true` on
  installs
- Keepalive cron pinging `/health` every ten minutes

**Exit:** every claim in the README is clickable.

## Phase 5 — Packaging

Historically where much of a winning submission's effort goes.

- Landing page with noscript block and Open Graph card
- Mobile check on a real phone
- `docs/` written: verification, uncertainty and assumptions, IBM stack map,
  architecture, deployment, Bob usage
- Three-minute demo video
- SkillsBuild certificate located and uploaded
- Submission page published

**Exit:** submitted before 31 August.

## Conditional

Attempted only if Phase 4 completes early. Each is defensible on its own terms
and none is load-bearing.

- **Delta-v surrogate.** A regressor trained on grid output, making the tool
  respond instantly instead of recomputing. The only machine learning with an
  honest job here. If built, MLflow becomes justified.
- **Knowledge graph over the corpus.** Questions to topics to existing tools to
  gaps, formalising the gap analysis currently asserted in prose. Rejected
  early under a lean-submission assumption; reopened now.
- **Validation drift monitoring.** Scheduled re-run of the validation suite
  against live Horizons data, recording agreement over time. Real monitoring of
  something that actually changes, unlike model drift on a deterministic solver.
- **Jupiter flyby option.** Project Lyra's central finding is that Oberth
  maneuvers make these missions feasible at all. Earth-direct first.
- **Voice reply** via browser SpeechSynthesis.

## Discipline

- Small branches with conventional prefixes, one concern each
- No aspirational entries in the README. If it is not built, it is not listed
- Bob spent on correctness-critical work and review passes, not scaffolding.
  40 Bobcoins per trial account is a budget
