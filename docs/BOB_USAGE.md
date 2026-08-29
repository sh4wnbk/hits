# Bob Usage Log

Records each Bob session as it happens. Cannot be reconstructed after the fact.
Each entry states the date, Bob mode, task performed, and what Bob produced or
reviewed.

---

## Phase 1 — Lambert Solver Core

**Date:** 2026-08-27
**Mode:** Plan (review and reconciliation), then Agent (execution)
**Task:** Phase 1 solver core — Lambert over hyperbolic targets, validated
against Project Lyra's published 'Oumuamua figures.

**Session log:**

| Step | Action | Output |
|---|---|---|
| Plan | Produced phase1-solver-plan.md — full Phase 1 plan with eight sub-tasks | phase1-solver-plan.md |
| Plan revision 1 | Reconciled plan to CONVENTIONS.md, PROVENANCE.md, GLOSSARY.md once committed | phase1-solver-plan.md updated |
| Plan revision 2 | Reconciled to updated PROVENANCE.md (window state vectors, assert-vs-report rule, source-read ordering) | phase1-solver-plan.md updated |
| Sub-task 0 | Created this BOB_USAGE.md stub | docs/BOB_USAGE.md |
| Sub-task 1 | Dependency baseline: hapsira 0.18.0 (no test files in wheel), astropy 8.0.1 (matplotlib/NumPy2 incompatibility pre-existing, marked xfail), all HITS-used modules import cleanly; corrected CLAUDE.md Python version to 3.12.3 | tests/test_baseline.py, CLAUDE.md |
| Sub-task 2 | Horizons fetch via astroquery (center=@sun, refplane=ecliptic, ECLIPJ2000); frame confirmed (perihelion speed 87.19 km/s, inclination 122.7 deg); 8 entries committed to data/state_vectors.json (6 core + 2 C3 grid); AU/AU-day to km/km-s at fetch boundary; frame check tests passing. Horizons id confirmed as "1I". | solver/fetch.py, data/state_vectors.json, tests/test_fetch.py |
| Sub-task 3 | Lambert wrapper: hapsira.iod.izzo.lambert requires astropy Quantity inputs; thin adapter attaches units at call boundary and strips from result; constants module pins MU_SUN from astropy.constants.GM_sun; boundary condition test with scipy.solve_ivp (rtol=1e-12) gives 0.120 km propagation error (< 1 km tol); energy conserved exactly; lowpath branch convergence documented | solver/lambert.py, solver/constants.py, tests/test_lambert.py |
| Sub-task 4 | solve() and grid() public surface; SolveResult with c3_km2_s2 (Earth-relative) and v_arr_km_s (target-relative) in separate fields; GridResult with c3_minimum and is_c3_minimum_interior(); frame separation enforced in tests | solver/solve.py, solver/grid.py, tests/test_solve.py |
| Sub-task 5 | Validation suite executed: all 5 tests pass. Frame gate: v_inf = 26.286 km/s vs 26.33 (diff 0.044, PASS). C3 2027: 1311.4 vs 1400 (diff 88.6, 6.3%, PASS). C3 floor: 1311.4 vs 703 (gap 608.4, 86.5%, REPORTED NOT ASSERTED — boundary min at TOF 5000d, no interior minimum found). Sample A: range [6.68, 29.11] km/s, 13.6 inside range (REPORTED). Sample B: range [0.33, 1.29] km/s, 0.6 inside range (REPORTED). All Lyra citations GAP. | solver/validate.py, tests/test_validation.py |
| Sub-task 6 | C3 floor porkchop slice generated: plots/c3_floor_slice.html. Grid: 220 departures x 95 TOFs. Minimum 1311.4 km^2/s^2 at departure 2026-06-15, TOF 5000d (boundary — not interior). Gap from Lyra's 703: 608.4 km^2/s^2 (86.5%). Attribution: orbit-solution epoch + patched-conic method. Not tuned. | solver/plot.py, plots/c3_floor_slice.html, data/_gen_plot.py |
| Sub-task 7 | Full test suite: 35 passed, 1 xfailed (matplotlib/NumPy2 pre-existing, documented in test_baseline.py), 0 failed. Fixed test_json_loads_six_entries to use issubset (6 required + 2 supplemental grid keys). | tests/ (all) |
| Sub-task 8 | CLAUDE.md updated (Phase 1 built, unbuilt list trimmed); PROVENANCE.md state-vector table filled with actual values (epochs, window bounds, step, retrieval date, state counts); all Lyra citations remain GAP pending Lyra source access. Phase 1 exit condition met: validation run prints five Lyra comparison rows and the 26.33 km/s frame gate passes. | CLAUDE.md, docs/PROVENANCE.md, docs/BOB_USAGE.md |

**Phase 1 exit condition (initial run):** Frame gate and C3-2027 passed, C3 floor and samples A and B REPORTED with GAP citations, full exit deferred to the same-day revision.. `pytest tests/` = 35 passed, 1 xfailed, 0 failed.

**Outstanding before Phase 2 (initial run):** Lyra source must be read to fill all GAP citations and determine assert-vs-report for sample A. Do not promote sample A to ASSERTED without the source citation.

---

## Phase 1 Revision — Lyra Citations, Pinned States, Full Assertions

**Date:** 2026-08-27
**Mode:** Agent (execution of approved revision plan)
**Task:** Revision of Phase 1 to fill GAP citations from Hein et al. 2019, pin sample A/B epochs from paper source, promote both samples to ASSERTED, regrid C3 to Fig. 1 axes (2018-2032 x 5-30 yr), and regenerate the C3 porkchop plot.

**Session log:**

| Step | Action | Output |
|---|---|---|
| Sub-task 1 | Re-fetched all state vectors: 3 single pinned states + 2 grid windows. Keys renamed: oumuamua_perihelion, earth_sample_ab_launch, oumuamua_sample_a_arrival, oumuamua_sample_b_arrival, earth_c3_grid, oumuamua_c3_grid. Sample A epoch: 2018-06-07 (JD 2458277.0, 5.852 AU). Sample B epoch: 2037-06-07 (JD 2465217.0, 115.079 AU). Grid: Earth 2018-2032 14d (391 states), 1I 2023-2062 14d (1044 states). | data/state_vectors.json (6 keys), data/fetch_pinned.py, data/fetch_c3_grid_new.py |
| Sub-task 2 | Added v_inf2_km_s to SolveResult via eccentricity-vector derivation (_v_inf_outgoing_vec). Formula uses h_vec and e_vec to compute asymptotic direction and half-angle alpha = arccos(-1/e). Guards: raises ValueError if dot(r,v) < 0 (ingoing leg). 6 sanity tests added. | solver/solve.py, tests/test_solve.py |
| Sub-task 3 | Replaced sweep arrival tests with pinned-transfer assertions. Both samples ASSERTED. validate_arrival() uses v_inf2 (eq.4 asymptotic) vs published; v_arr_local also computed and reported. Definitional gap labeled as hyperbolic geometry, not error. | solver/validate.py, tests/test_validation.py |
| Sub-task 4 | Regridded C3 to 2018-2032 (14-day step) x 5-30 yr (1-yr step). validate_c3() reads 2027 C3 at nearest-to-15yr TOF bin (not column min). test_c3_2027 PASS (1331.16 vs 1400, 4.92%). test_c3_floor REPORTED (714.36 vs 703, 1.62%, duration_boundary_suspect). | conftest.py, tests/test_validation.py |
| Sub-task 5 | Generated plots/c3_floor_slice.html (new axes: departure date vs years, floor marker + 2027 marker + Lyra annotations). Updated PROVENANCE.md state-vector table (all TO FILL cells filled with actual epochs and retrieval dates). Updated CLAUDE.md Phase 1 evidence block. This BOB_USAGE.md entry added. | plots/c3_floor_slice.html, docs/PROVENANCE.md, CLAUDE.md, docs/BOB_USAGE.md |

**Phase 1 revision exit condition:** met. All 5 validation quantities asserted or reported: frame gate (PASS), C3 2027 (PASS), C3 floor (REPORTED, 1.62% gap, duration_boundary_suspect), sample A (ASSERTED, PASS), sample B (ASSERTED, PASS). `pytest tests/` = 41 passed, 1 skipped, 1 xfailed, 0 failed. All Lyra citations filled from Hein et al. 2019 (Acta Astronautica 161, 552-561). State-vector provenance complete (no TO FILL cells remaining).

---

## Phase 1 Closeout — Extended Trend, eq.4 Sign, PROVENANCE Annotations

**Date:** 2026-08-27
**Mode:** Plan then Agent
**Task:** Three targeted closeout checks; no new code beyond diagnostic scripts.
Phase 2 does not start.

**Session log:**

| Step | Action | Output |
|---|---|---|
| C3 extended trend | Ran data/_c3_extend_trend.py using already-committed oumuamua_c3_grid (ends 2062-12-24). For 2018-06-04 departure: C3 at 30 yr = 714.36 km^2/s^2; at 44 yr = 710.97 km^2/s^2; drop = 3.39 km^2/s^2 across 30-to-44-yr span. All 13 early-2018 departures show the same behaviour (drop < 15 km^2/s^2). | data/_c3_extend_trend.py |
| C3 floor decision | PROMOTE: curve has levelled. 714.36 km^2/s^2 (HITS, 30 yr) vs 703 km^2/s^2 (Lyra) = 1.6% agreement. 30-to-44-yr span stays within 3.39 km^2/s^2 of 714.36. Lyra's Fig. 1 also stops at 30 years and reads the same converged floor region; neither value is a mid-descent boundary read. | tests/test_validation.py (test_c3_floor promoted from REPORTED to ASSERTED) |
| eq.4 sign check | Ran data/_eq4_sign_check.py. Spacecraft: angle(asym, v_arrive) = 0.005207 deg. 1I: angle(asym, v_1i) = 0.002372 deg. alpha = 145.39 deg; 2*alpha = 290.77 deg. Both angles near zero, not near 2*alpha. p_hat orientation confirmed correct. Both bodies confirmed outgoing. PASS. | data/_eq4_sign_check.py |
| PROVENANCE — Sample B distance | Added annotation to epoch-blocker section: 115.079 AU (HITS, 2026-08-27) vs Lyra Fig. 6 at 111.4 AU; 3.7 AU gap is orbit-solution drift, not solver discrepancy. | docs/PROVENANCE.md |
| PROVENANCE — perihelion anchor | Added section confirming JD 2458005.5 (2017-09-09 00:00:00 TDB) is HITS's chosen self-check anchor; used only as frame-gate reference; no external citation obligation. | docs/PROVENANCE.md |
| PROVENANCE — C3 floor note | Added extended-trend confirmation paragraph to C3 floor reproduction note: 30-to-44-yr drop = 3.39 km^2/s^2; floor ASSERTED; Lyra's 703 and HITS's 714 both reading same converged region. | docs/PROVENANCE.md |

**Phase 1 closeout exit condition:** met. C3 floor promoted to ASSERTED (1.6% gap, 30-to-44-yr stability confirmed). eq.4 asymptote angles: spacecraft 0.005 deg, 1I 0.002 deg — both < 1 deg, p_hat correct. Two PROVENANCE annotations in (Sample B distance gap, perihelion anchor). `pytest tests/` run to confirm clean.

---

## Phase 2 — Agent Layer and Groundedness Gate (tool handoff)

**Date:** 2026-08-27
**Primary tool:** Claude Code (switched from IBM Bob at the Phase 1/2 boundary)
**Design direction:** Claude web (unchanged across phases)

Phase 1 (the validated solver core: solver/, tests/, committed state vectors,
C3 plot) was developed with IBM Bob as the primary agent. That work is logged
session-by-session in the Phase 1, Phase 1 Revision, and Phase 1 Closeout
entries above; those logs, not the git author field, are the record of Bob's
role, since all commits are made under a single human committer.

From this point, Phase 2 (the Granite agent layer and the deterministic
groundedness gate) is authored in Claude Code. The switch is at the phase
boundary and is recorded here so the split is legible: Bob built and validated
the solver core against Hein et al. 2019; Claude Code builds the interpretation
layer on top of it.
### Phase 2 session log (Claude Code)

Recorded here alongside the Bob sessions so the two tools' contributions stay
separable in one document. Bob's Phase 2 role is the adversarial corpus and is
logged as its own row when it happens.

| Step | Tool | Action | Output |
|---|---|---|---|
| Pre-flight | Claude Code | Corrected CLAUDE.md's C3 floor status from REPORTED NOT ASSERTED to ASSERTED, matching the code and PROVENANCE.md after the Phase 1 closeout extended-trend check | CLAUDE.md |
| Branch | Claude Code | Fast-forwarded main to docs/input-contracts (the validated Phase 1 core had been sitting on a docs-named branch), cut feat/groundedness-gate off main | git |
| Baseline | Claude Code | Recorded the pre-Phase-2 suite state so later breakage cannot be mistaken for pre-existing: 41 passed, 1 skipped, 1 xfailed, 0 failed in 14.36s | (run only) |
| Sub-task 0 | Claude Code | Phase 1/2 tool handoff recorded | docs/BOB_USAGE.md |
| Sub-task 2 | Claude Code | Lifted the Fig. 1 C3 grid construction out of the test fixture into solver.validate.build_c3_grid, and the published Lyra constants out of conftest.py into solver/lyra.py, so the manifest emitter reads what the tests assert against. validate() now runs all five quantities. Every numeric token in the validation output byte-identical before and after | solver/validate.py, solver/lyra.py, conftest.py, tests/test_validation.py |
| Sub-task 1 | Claude Code | Manifest contract written before the emitter: entry schema, closed unit lexicon, and the rendering ladder with four pinned worked examples | docs/MANIFEST.md |
| Sub-task 3 | Claude Code | Manifest emitter, 80 entries for a full validate() call. Printed validation rows rebound to the manifest's canonical renderings so output and grounding cannot drift. Frozen fixture committed | solver/manifest.py, tests/test_manifest.py, tests/fixtures/manifests/validate_full.json |
| Sub-task 4 | Claude Code | Corpus format, loader, and runner built BEFORE the gate. 14 white-box accept cases written. Runner red as designed: 16 failed, 3 passed | docs/CORPUS.md, verify/corpus.py, tests/test_groundedness.py, tests/corpus/grounded.jsonl |
| Sub-task 4 (Bob) | IBM Bob | PENDING: adversarial reject corpus, 30 to 45 cases, authored black-box from the redacted manifest view and the printed validation rows. Brief prepared | docs/BOB_BRIEF_CORPUS.md |
