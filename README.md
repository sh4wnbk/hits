# HITS | Hyperbolic Intercept & Trajectory Solver

*Can we catch it? Expert-level intercept analysis, open to everyone.*

The intercept math exists. It has existed at NASA and in aerospace tools since
1964, most of it is free, and some of it is a download away. What it is not is
reachable.

| Tool | Status | What stands between you and an answer |
|---|---|---|
| [GMAT](https://software.nasa.gov/software/GSC-17177-1) (NASA) | Free, open source | Mission-design expertise. It is an environment to work in, not a question you can ask |
| [OITS](https://github.com/AdamHibberd/Optimum_Interplanetary_Trajectory) (Project Lyra) | Free, open source | MATLAB, the SPICE toolkit, and the NOMAD optimizer, plus knowing which bodies to sequence |
| OTIS (NASA Glenn) | Free, export-controlled | ITAR. Not releasable to, or usable by, anyone who is not a United States person |
| TRACE (The Aerospace Corporation) | Internal | Never publicly released |

So the capability is not missing. It is locked away, behind expertise in three
of those rows and behind citizenship in the fourth, and the people it is locked
away from are the ones asking. 3,171 questions pulled out of 19,122 comments on
six NASA JPL videos say what they want to know, and the two largest technical
themes are how long it would take and whether we could catch it. None of those
people is going to install GMAT.

HITS is that capability with the barrier removed. It computes real intercept
trajectories over the hyperbolic orbits of all three interstellar objects
humanity has found, 1I/'Oumuamua, 2I/Borisov and 3I/ATLAS, and says in plain
language what such a mission would cost. Every number in an answer is checked
against solver output before it is shown, and every answer carries a field
saying what backs it: 'Oumuamua's says its figures were validated against
Project Lyra's published study, and Borisov's and 3I/ATLAS's say they were
computed by the same method and that no published intercept study exists to
validate them against, because none does.

**Status.** The solver, the three-object set, the groundedness gate, and the
agent layer are built and tested (202 passed, 1 skipped, 1 xfailed). The API,
the web frontend, the judges endpoints, and the deployment are not built yet,
and nothing below describes them as though they were.

---

## The exchange

> **You ask:** Can we catch 'Oumuamua?
>
> **HITS answers:**
>
> A transfer to the target exists for the departure asked about. Leaving Earth
> on 2017-06-07 and arriving on 2018-06-07, the flight time is 365 days, or 1
> year.
>
> Reaching it from an Earth-relative departure costs 393.34 km^2/s^2 of
> characteristic energy, which is a hyperbolic excess speed of 19.8328 km/s once
> clear of Earth.
>
> The probe would meet the target at 13.71605 km/s in the target-relative frame,
> which is the speed it passes at. Its asymptotic arrival relative velocity, the
> quantity the mission-design literature compares against, is 13.96737 km/s.
>
> What HITS settles here is the trajectory, not the launch vehicle. It computes
> what the transfer costs and does not model launcher capability, so the
> departure energy above is the input to a feasibility judgement rather than the
> judgement itself.
>
> All figures are patched-conic, two-body. HITS does not perform n-body
> integration and does not model non-gravitational forces, so a figure is a
> faithful record of what the solver computed rather than a claim that it is
> right to the precision it is quoted at.

Verbatim from a live run on 2026-08-30, `served_by: deterministic_floor`. That
label is the interesting part. Granite was called three times and rejected three
times, because it kept rewriting the date `2017-06-07` as "June 7, 2017", and a
`7` that the solver never emitted is a number the gate will not pass. So the
system served its deterministic floor instead: correct, grounded, and visibly
credited to the template rather than to the model. Nothing in this repository
serves an ungrounded number, including when the model is the thing at fault.

## The demand

![Questions asked, by theme](plots/demand_clusters.png)

3,171 questions pulled out of 19,122 comments on six NASA JPL videos and
clustered. Travel time and intercept are the two largest technical themes, and
they are the two HITS answers. The largest clusters in the corpus overall are
not technical at all, and the chart shows those too.

<p align="center">
  <img src="docs/img/3I_ATLAS.PNG" width="15%" alt="3I/ATLAS approaching Mars">
  <img src="docs/img/3I.ATLAS.PNG" width="15%" alt="What we know about 3I/ATLAS">
  <img src="docs/img/Oumuamua.PNG" width="15%" alt="First interstellar asteroid">
  <img src="docs/img/TRAPPIST-1.PNG" width="15%" alt="TRAPPIST-1">
  <img src="docs/img/curiosity_rover_animation.PNG" width="15%" alt="Curiosity rover animation">
  <img src="docs/img/7_minutes_of_terror.PNG" width="15%" alt="Seven minutes of terror">
</p>

The six NASA JPL videos the demand was read from.

---

## Problem statement

The claim is not that no software exists. It is the narrower and defensible
one: no *accessible* tool exists. Every tool in the table at the top of this
page is real, three of the four are free, and not one of them will answer a
question put to it by somebody who does not already know how to ask.

How the demand above was measured, with the extraction rule, the clustering
parameters, and the stated limits, is in `docs/EVIDENCE.md`; the corpora and
the cluster report are in `/data`.

## Solution description

HITS takes one of the three interstellar objects, computes a real intercept
trajectory over its hyperbolic orbit, and says in plain language what such a
mission would cost. One URL, no clone, no orbital mechanics, and every number
in the answer is checked against solver output before it is shown.

The three are a committed set and not a text field. A typed designation would
need a live Horizons call at request time, which would put a judge's re-run at
the mercy of the network and end the guarantee that the same numbers come back
every time. `solver/objects.py` holds the set, and asking for anything else
raises rather than guessing.

What it is not is load-bearing, because it is what keeps the claim narrow.
HITS is not a replacement for GMAT and answers one question rather than many.
It is not a classifier of natural versus artificial objects, a question
observational data answers and orbital elements do not. It does not model
launch-vehicle capability, so it reports what a transfer costs and leaves the
go/no-go judgement to the reader. It models patched-conic transfers, not
n-body integration, and does not model non-gravitational forces.

## AI approach and architecture

```mermaid
flowchart LR
  H[JPL Horizons<br/>via astroquery] --> S
  SBDB[Small-Body Database<br/>designation only] -.-> S
  S[solver/<br/>hapsira Lambert, grids] --> M[solver/manifest.py<br/>every citable number]
  M --> A[agent/<br/>Granite explains]
  M --> V[verify/<br/>groundedness gate]
  A --> V
  V --> R[grounded explanation<br/>or deterministic floor]
```

The solver computes and the model interprets. That split is enforced by
ordering: the solver runs first and completes, the agent receives structured
output, and the agent cannot trigger a recomputation with different
parameters. Because the set of legitimate numbers is therefore fixed before
generation begins, the check is tractable. `solver/manifest.py` emits every
citable quantity for a call, one canonical value with several declared
renderings from a pinned ladder, and `verify/groundedness.py` compares every
numeric token in a candidate explanation against that index. Membership is
dispositive and the matching path performs no arithmetic at all, which an AST
test enforces.

A rejected candidate is regenerated at most twice with the specific rejected
tokens fed back. If it still fails, `agent/template.py` serves a deterministic
floor built only from manifest renderings, and that floor is gated like any
other candidate. Every response carries `served_by`, one of
`granite_first_pass`, `granite_after_regen` or `deterministic_floor`, so a
templated answer is never mis-credited to Granite. If watsonx is unreachable
or no credentials are present, the numbers still compute and still render.

That loop is what the exchange at the top of this page is showing: three
Granite attempts rejected, the floor served, the label saying so. The gate
certifies grounding, not truth, which is a different and sharper limit, stated
in full under Limits.

## Selected challenge theme

August Space Exploration Challenge, solution area: mission planning and
optimization. The demand measured above is a trajectory optimization question
being asked by people who cannot run a trajectory optimizer, so HITS approaches
that solution area from the accessibility side rather than the capability side.

## How IBM Bob was used

IBM Bob was the primary development tool for Phase 1, the part that computes:
the Lambert solver over hyperbolic targets, the Horizons fetch and committed
state vectors, the grid, the C3 plot, and the validation suite against Hein et
al. 2019. Bob then authored the 35-case adversarial corpus black-box, without
sight of the gate it attacks. Claude Code took over at the Phase 1/2 boundary
for the groundedness gate and the agent layer.

Every commit here is authored by one human committer, so git carries no tool
authorship and the record of which tool did what is `docs/BOB_USAGE.md`,
written session by session as the work happened. `docs/HARNESS.md` describes
the process discipline both tools worked under.

## Verification

The solver reproduces five published quantities from Project Lyra's
'Oumuamua study (Hein et al. 2019, Acta Astronautica 161, 552-561). The
largest disagreement is 4.92%. Every row below is 1I/'Oumuamua, and there is
no equivalent table for the other two objects because there is nothing to put
in it: no intercept study has been published for 2I/Borisov or 3I/ATLAS. They
are computed by the same method, over state vectors fetched down the same path
and frame-checked against the elements Horizons reports for the same body at
the same epoch, and validated against nothing. Each object carries that
distinction as a `verification_status` field rather than as a footnote, so a
reader who sees only one answer still sees what backs it.

| Quantity | HITS | Published | Difference |
|---|---|---|---|
| Perihelion v_inf (frame gate) | 26.286 km/s | 26.33 km/s | 0.044 km/s |
| C3, 2027 launch | 1331.16 km²/s² | 1400 km²/s² | 4.92% |
| C3 floor | 714.36 km²/s² | 703 km²/s² | 1.62% |
| Sample A arrival v_inf2 | 13.967 km/s | 13.6 km/s | 0.367 km/s |
| Sample B arrival v_inf2 | 0.642 km/s | 0.6 km/s | 0.042 km/s |

![HITS against published Lyra figures](plots/validation_comparison.png)

Every quantity on a unit-free axis against the tolerance declared for it. The
interactive version with hover detail is `plots/validation_comparison.html`.

The remaining gaps are attributed to orbit-solution epoch drift between Lyra's
2019 ephemeris and the 2026-08-27 retrieval, and that attribution is argued
rather than asserted in `docs/PROVENANCE.md`. Full claim-and-step table, with
every unbuilt check named as unbuilt: `docs/VERIFICATION.md`.

The criteria-to-evidence mapping will live on the judges page at `/judges`,
which is the next build. Until it ships, the mapping is this section and
`docs/VERIFICATION.md`.

## Limits

HITS models patched-conic transfers. It does not perform n-body integration,
does not model solar radiation pressure or other non-gravitational forces, and
has no launch-vehicle model, so delta-v is a requirement rather than a
capability match. Horizons ephemerides update as observations accumulate, so
numbers carry the date they were computed.

The gate has standing limits of its own, and they are written down because a
gate whose limits are unstated invites the belief that it has none. It cannot
see a real number attached to the wrong result within one manifest; two such
cases are held as accepted limits in `tests/corpus/known_limits.jsonl` rather
than counted as catches. It cannot say what kind of wrong a number is, because
telling a near-miss from an invention means arithmetic it is forbidden, so
both are rejected as `fabricated-number`. Granite Guardian is not wired in and
every verdict reports its advisory field as unavailable.

Most importantly, a grounded explanation is not necessarily a correct one. The
first live run on 2026-08-30 returned an explanation carrying only manifest
renderings that still said the 2027 C3 comparison "exceeds the solver's
tolerance of 20%" when 4.92% is inside it. Every number was grounded and the
claim about them was false. Membership and attribution do not check a
comparative assertion.

## Run it

The deployment is not built. Today HITS runs locally, and the validation runs
offline against committed state vectors with no credentials and no network.

```
python -m venv .venv && . .venv/bin/activate
pip install --no-deps -r requirements.txt
pytest                              # full suite
pytest tests/test_validation.py -v  # the five Lyra comparisons, printed
```

Python 3.12. `--no-deps` is deliberate and `docs/VERIFICATION.md` explains it:
requirements.txt is a complete pinned set, and resolving hapsira's matplotlib
bound would downgrade NumPy, which would change computed numbers. The same
install and suite run in CI on every push (`.github/workflows/ci.yml`).

The explanation layer is the only part that reads a credential;
copy `.env.example` to `.env` to supply watsonx settings. Without it, the
solver runs unchanged and explanations are served by the deterministic floor.

## Repository layout

```
solver/   orbital mechanics, the three-object set, validation, manifest emitter
verify/   extraction rule, groundedness gate, adversarial corpus loader
agent/    Granite client, generate-and-gate loop, deterministic floor
tests/    202 tests, including the corpus and the invariant proofs
data/     comment corpora, cluster report, committed state vectors, Lyra PDF
docs/     architecture, verification, manifest contract, process record
specs/    mission, tech stack, roadmap
plots/    C3 porkchop slice
```

## Documents

- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`
- `docs/EVIDENCE.md`
- `docs/VERIFICATION.md`
- `docs/ARCHITECTURE.md`
- `docs/MANIFEST.md`
- `docs/CORPUS.md`
- `docs/PROVENANCE.md`
- `docs/CONVENTIONS.md`
- `docs/GLOSSARY.md`
- `docs/IBM_STACK.md`
- `docs/BOB_USAGE.md`
- `docs/HARNESS.md`
- `CLAUDE.md`
