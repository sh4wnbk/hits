"""
solver/validate.py — public validate() function and validation sub-functions.

Implements the three validation quantities from the Phase 1 plan, each in its
own frame:

  1. validate_frame_gate(sv)
     Heliocentric frame: v_inf = sqrt(v^2 - 2*mu/r) against 26.33 km/s.
     Run first. All other validation is skipped if this fails.
     Formula per GLOSSARY.md: square root of a DIFFERENCE OF SQUARES,
     never the difference of the square roots.

  2. validate_c3(earth_svs, oumuamua_svs, tof_days_array)
     Earth-relative departure frame: C3 grid over the 2027 window.
     Compared against 1400 km^2/s^2 (2027 best) and 703 km^2/s^2 (floor).

  3. validate_arrival(earth_svs, target_svs, tof_days, published_v_arr)
     Target-relative arrival frame: sweep over launch window at fixed TOF.
     Reports range against published scalar. Assert vs report follows source
     precision (determined at Sub-task 2 source read; currently GAP).

Fidelity: patched-conic, two-body. No n-body integration.
Citations: GAP until Lyra source is read (PROVENANCE.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from solver.constants import MU_SUN
from solver.fetch import StateVector
from solver.grid import grid as _grid, GridResult
from solver.solve import solve


# ---------------------------------------------------------------------------
# 1. Frame gate — heliocentric v_inf
# ---------------------------------------------------------------------------

@dataclass
class FrameGateResult:
    computed_km_s: float
    published_km_s: float
    abs_diff_km_s: float
    rel_diff_pct: float
    tolerance_km_s: float
    passed: bool
    citation: str
    formula: str = "sqrt(v^2 - 2*mu/r)"
    fidelity_note: str = "Patched-conic, 2-body only. No n-body integration."


def validate_frame_gate(
    sv: StateVector,
    published_km_s: float = 26.33,
    tolerance_km_s: float = 0.5,
    citation: str = "GAP: page/table to be filled from Lyra source",
) -> FrameGateResult:
    """
    Compute heliocentric v_inf and compare against published value.

    Formula (GLOSSARY.md): v_inf = sqrt(v^2 - 2*mu/r)
    This is the square root of the difference of squares.
    NEVER compute v - v_esc (difference of speeds); that is wrong.

    mu is imported from solver.constants, never redefined locally.
    """
    v2 = np.dot(sv.v, sv.v)
    r  = sv.distance_km
    val = v2 - 2.0 * MU_SUN / r
    if val < 0.0:
        computed = 0.0
    else:
        computed = math.sqrt(val)

    abs_diff = abs(computed - published_km_s)
    rel_diff = 100.0 * abs_diff / published_km_s
    passed = abs_diff <= tolerance_km_s

    return FrameGateResult(
        computed_km_s=round(computed, 5),
        published_km_s=published_km_s,
        abs_diff_km_s=round(abs_diff, 5),
        rel_diff_pct=round(rel_diff, 3),
        tolerance_km_s=tolerance_km_s,
        passed=passed,
        citation=citation,
    )


def print_frame_gate(result: FrameGateResult, manifest=None) -> None:
    """
    Print the frame-gate comparison row.

    Numbers come from the manifest's canonical renderings, not from format
    specifiers held here. That binding is the point: the rows a judge reads and
    the set of numbers an explanation is allowed to quote are the same strings,
    so they cannot drift apart. tests/test_groundedness.py runs the gate over
    this output to prove it.
    """
    if manifest is None:
        from solver.manifest import Manifest, _frame_gate_entries
        manifest = Manifest(producer="validate", entries=_frame_gate_entries(result))
    c = manifest.canonical
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"FRAME GATE | v_inf_helio  [formula: {result.formula}]")
    print(f"  computed:   {c('validate.frame_gate.computed')} km/s")
    print(f"  published:  {c('validate.frame_gate.published')} km/s  ({result.citation})")
    print(f"  abs diff:   {c('validate.frame_gate.abs_diff')} km/s")
    print(f"  rel diff:   {c('validate.frame_gate.rel_diff_pct')}%")
    print(f"  tolerance:  {c('validate.frame_gate.tolerance')} km/s")
    print(f"  {status}")
    print(f"  NOTE: {result.fidelity_note}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# 2. Departure C3 — Earth-relative frame
# ---------------------------------------------------------------------------

@dataclass
class C3Result:
    """C3 validation in Earth-relative frame."""
    # 2027 launch column minimum
    c3_2027_computed_km2_s2: float
    c3_2027_published_km2_s2: float
    c3_2027_abs_diff: float
    c3_2027_rel_diff_pct: float
    c3_2027_tolerance_frac: float
    c3_2027_passed: bool
    c3_2027_departure_jd: float
    c3_2027_tof_days: float
    c3_2027_citation: str

    # Global floor (grid minimum)
    c3_floor_computed_km2_s2: float
    c3_floor_published_km2_s2: float
    c3_floor_abs_diff: float
    c3_floor_rel_diff_pct: float
    c3_floor_tolerance_frac: float
    c3_floor_passed: bool
    c3_floor_departure_jd: float
    c3_floor_tof_days: float
    c3_floor_citation: str
    c3_floor_edge_type: str   # "physical_launch_edge", "duration_boundary_suspect", "interior"
    c3_floor_gap_attribution: str

    retrieval_date: str
    fidelity_note: str = "Patched-conic, 2-body. Gap attribution: orbit-solution epoch and patched-conic method."


def _classify_floor_edge(
    floor_dep_jd: float,
    floor_tof_days: float,
    all_dep_jds: np.ndarray,
    all_tof_days: np.ndarray,
) -> str:
    """
    Classify the C3 floor minimum location per PROVENANCE.md rules.

    Returns one of:
      "physical_launch_edge"       — floor is in first two launch columns (~28 d
                                     of 2018-01-01). Physical, not suspected.
      "duration_boundary_suspect"  — floor is at the first or last duration row
                                     (5 yr or 30 yr) and NOT on launch edge.
                                     Suspect: duration range may be too narrow.
      "interior"                   — floor is not on any edge.
    """
    # Check launch edge: floor departure within 28 days of the earliest launch
    earliest_dep = float(all_dep_jds[0])
    if floor_dep_jd <= earliest_dep + 28.0:
        return "physical_launch_edge"

    # Check duration boundary (5 yr or 30 yr edges)
    tol_days = 15.0   # half a 30-day step margin
    if (abs(floor_tof_days - float(all_tof_days[0]))  < tol_days or
            abs(floor_tof_days - float(all_tof_days[-1])) < tol_days):
        return "duration_boundary_suspect"

    return "interior"


def validate_c3(
    grid_result,
    c3_2027_published: float = 1400.0,
    c3_2027_tolerance_frac: float = 0.20,
    c3_2027_citation: str = "Hein et al. 2019, p.554 col 1",
    c3_floor_published: float = 703.0,
    c3_floor_tolerance_frac: float = 0.20,
    c3_floor_citation: str = "Hein et al. 2019, p.553 col 2 / Fig.1",
    retrieval_date: str = "see data/state_vectors.json",
) -> C3Result:
    """
    Validate C3 grid against Lyra published figures (Hein et al. 2019).

    Both quantities are in the Earth-relative departure frame.
    They are never compared against heliocentric v_inf figures.

    c3_2027 : minimum over 2027 launch column (JD 2461041-2461406).
    c3_floor : global grid minimum. Floor edge-type classified separately.

    Gap is attributed to orbit-solution epoch drift (retrieval date vs 2019)
    and patched-conic method. Not tuned away.
    """
    from astropy.time import Time as _Time

    dep_jds  = grid_result.departure_jds
    tof_days = grid_result.tof_days
    c3_grid  = grid_result.c3_grid

    # --- 2027 column minimum ---
    # Calendar year 2027: JD 2461041 (2027-Jan-01) to JD 2461406 (2027-Dec-31)
    jd_2027_start = _Time("2027-01-01 00:00:00", format="iso", scale="tdb").jd
    jd_2027_end   = _Time("2027-12-31 00:00:00", format="iso", scale="tdb").jd
    col_mask = (dep_jds >= jd_2027_start) & (dep_jds <= jd_2027_end)

    # Target TOF for 2027 C3: the paper quotes ~15-year duration (p.554 col 1).
    # Find the TOF bin nearest to 15 years and read the C3 from that row.
    # This is a direct read at the paper's stated duration, not a column minimum.
    tof_target_days = 15.0 * 365.25
    tof_nearest_idx = int(np.argmin(np.abs(tof_days - tof_target_days)))

    if not np.any(col_mask):
        # No 2027 departures in grid; fall back: nearest TOF row, global argmin on launch
        row = c3_grid[:, tof_nearest_idx]
        dep_idx = int(np.nanargmin(row))
        c3_2027_val    = float(row[dep_idx])
        c3_2027_dep_jd = float(dep_jds[dep_idx])
        c3_2027_tof    = float(tof_days[tof_nearest_idx])
    else:
        sub_grid = c3_grid[col_mask, :]
        sub_jds  = dep_jds[col_mask]
        # Read C3 at the nearest-to-15yr duration row, take min over 2027 launch dates
        col_at_15yr = sub_grid[:, tof_nearest_idx]
        dep_idx = int(np.nanargmin(col_at_15yr))
        c3_2027_val    = float(col_at_15yr[dep_idx])
        c3_2027_dep_jd = float(sub_jds[dep_idx])
        c3_2027_tof    = float(tof_days[tof_nearest_idx])

    c3_2027_abs = abs(c3_2027_val - c3_2027_published)
    c3_2027_rel = 100.0 * c3_2027_abs / c3_2027_published
    c3_2027_ok  = c3_2027_abs <= c3_2027_tolerance_frac * c3_2027_published

    # --- Global floor ---
    floor_min, floor_dep_jd, floor_tof = grid_result.c3_minimum
    c3_floor_abs = abs(floor_min - c3_floor_published)
    c3_floor_rel = 100.0 * c3_floor_abs / c3_floor_published
    c3_floor_ok  = c3_floor_abs <= c3_floor_tolerance_frac * c3_floor_published

    # Edge-type classification per PROVENANCE.md
    edge_type = _classify_floor_edge(floor_dep_jd, floor_tof, dep_jds, tof_days)

    # Date only, not the full retrieved_utc timestamp. The manifest declares
    # the retrieval date as retrieval_date[:10] and renders it as itself, so a
    # printed time-of-day is a number no manifest entry carries. The dogfood
    # test in tests/test_groundedness.py caught exactly that.
    gap_attr = (
        f"orbit-solution epoch ({retrieval_date[:10]}) + patched-conic method. "
        f"Not tuned away."
    )

    return C3Result(
        c3_2027_computed_km2_s2=round(c3_2027_val, 2),
        c3_2027_published_km2_s2=c3_2027_published,
        c3_2027_abs_diff=round(c3_2027_abs, 2),
        c3_2027_rel_diff_pct=round(c3_2027_rel, 2),
        c3_2027_tolerance_frac=c3_2027_tolerance_frac,
        c3_2027_passed=c3_2027_ok,
        c3_2027_departure_jd=c3_2027_dep_jd,
        c3_2027_tof_days=c3_2027_tof,
        c3_2027_citation=c3_2027_citation,
        c3_floor_computed_km2_s2=round(floor_min, 2),
        c3_floor_published_km2_s2=c3_floor_published,
        c3_floor_abs_diff=round(c3_floor_abs, 2),
        c3_floor_rel_diff_pct=round(c3_floor_rel, 2),
        c3_floor_tolerance_frac=c3_floor_tolerance_frac,
        c3_floor_passed=c3_floor_ok,
        c3_floor_departure_jd=floor_dep_jd,
        c3_floor_tof_days=floor_tof,
        c3_floor_citation=c3_floor_citation,
        c3_floor_edge_type=edge_type,
        c3_floor_gap_attribution=gap_attr,
        retrieval_date=retrieval_date,
    )


def print_c3_result(result: C3Result, manifest=None) -> None:
    """
    Print both C3 comparison rows, Earth-relative frame.

    Manifest-bound for the same reason as print_frame_gate.
    """
    if manifest is None:
        from solver.manifest import Manifest, _c3_entries
        manifest = Manifest(producer="validate", entries=_c3_entries(result))
    c = manifest.canonical
    print(f"\n{'='*60}")
    print("C3 VALIDATION | Earth-relative departure frame")
    print("  2027 launch column minimum:")
    print(f"    computed:   {c('validate.c3.y2027.computed')} km^2/s^2  "
          f"(departure {c('validate.c3.y2027.departure.iso')}, "
          f"TOF {c('validate.c3.y2027.tof_years')} yr)")
    print(f"    published:  {c('validate.c3.y2027.published')} km^2/s^2  ({result.c3_2027_citation})")
    print(f"    abs diff:   {c('validate.c3.y2027.abs_diff')} km^2/s^2")
    print(f"    rel diff:   {c('validate.c3.y2027.rel_diff_pct')}%")
    print(f"    tolerance:  {c('validate.c3.y2027.tolerance_pct')}%")
    print(f"    {'PASS' if result.c3_2027_passed else 'FAIL'}")
    print("  C3 floor (global grid minimum):")
    print(f"    computed:   {c('validate.c3.floor.computed')} km^2/s^2  "
          f"(departure {c('validate.c3.floor.departure.iso')}, "
          f"TOF {c('validate.c3.floor.tof_years')} yr)")
    print(f"    published:  {c('validate.c3.floor.published')} km^2/s^2  ({result.c3_floor_citation})")
    print(f"    abs diff:   {c('validate.c3.floor.abs_diff')} km^2/s^2")
    print(f"    rel diff:   {c('validate.c3.floor.rel_diff_pct')}%")
    print(f"    tolerance:  {c('validate.c3.floor.tolerance_pct')}%")
    print(f"    edge type:  {result.c3_floor_edge_type}")
    print(f"    gap attribution: {result.c3_floor_gap_attribution}")
    print(f"    {'PASS' if result.c3_floor_passed else 'FAIL'}")
    print(f"  {result.fidelity_note}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# 3. Arrival relative velocity sweep — target-relative frame
# ---------------------------------------------------------------------------

@dataclass
class ArrivalResult:
    """
    Result of a single pinned Lambert transfer for sample validation.

    Both samples use pinned launch and arrival epochs from the Lyra source.
    Epoch blocker is resolved (PROVENANCE.md): both samples share launch
    2017-06-07 12:00:00 TDB. Assert both.

    Two arrival velocities are reported (per PROVENANCE.md definitional note):
      v_arr_local_km_s : HITS native local encounter relative velocity.
      v_inf2_km_s      : eq.4 of Hein et al. 2019, asymptotic difference.
    The published figure (13.6 / 0.6 km/s) is compared against v_inf2.
    The definitional gap |v_inf2 - v_arr_local| is reported separately.
    """
    sample_label: str
    tof_days: float
    launch_epoch_jd: float
    arrival_epoch_jd: float
    encounter_distance_au: float   # target distance at arrival / AU_TO_KM
    v_arr_local_km_s: float        # HITS native local encounter relative velocity
    v_inf2_km_s: float             # eq.4 asymptotic: compared against published
    published_km_s: float          # Lyra published figure
    abs_diff_km_s: float           # |v_inf2 - published|
    rel_diff_pct: float
    tolerance_km_s: float
    passed: bool
    definitional_gap_km_s: float   # |v_inf2 - v_arr_local|; geometry, not error
    citation: str
    fidelity_note: str = "Patched-conic, 2-body. Target-relative arrival frame."


def validate_arrival(
    earth_sv: StateVector,
    target_sv: StateVector,
    tof_days: float,
    published_km_s: float,
    tolerance_km_s: float,
    sample_label: str,
    citation: str = "Hein et al. 2019 (Lyra paper)",
) -> "ArrivalResult":
    """
    Validate a single pinned Lambert transfer against the Lyra published figure.

    Compares v_inf2 (eq.4 asymptotic) against the published value.
    Also reports v_arr_local (HITS native) and the definitional gap.

    Parameters
    ----------
    earth_sv : StateVector — Earth state at launch epoch.
    target_sv : StateVector — Target state at arrival epoch.
    tof_days : float — time of flight in days (derived from pinned epochs).
    published_km_s : float — Lyra published arrival relative velocity (eq.4).
    tolerance_km_s : float — assertion tolerance.
    sample_label : str — human label for this sample.
    citation : str — source citation.
    """
    from solver.constants import AU_TO_KM

    result = solve(earth_sv, target_sv, tof_days)

    abs_diff = abs(result.v_inf2_km_s - published_km_s)
    rel_diff = 100.0 * abs_diff / published_km_s if published_km_s > 0 else 0.0
    passed = abs_diff <= tolerance_km_s
    def_gap = abs(result.v_inf2_km_s - result.v_arr_km_s)
    encounter_au = target_sv.distance_km / AU_TO_KM

    return ArrivalResult(
        sample_label=sample_label,
        tof_days=tof_days,
        launch_epoch_jd=earth_sv.epoch_tdb_jd,
        arrival_epoch_jd=target_sv.epoch_tdb_jd,
        encounter_distance_au=round(encounter_au, 3),
        v_arr_local_km_s=round(result.v_arr_km_s, 5),
        v_inf2_km_s=round(result.v_inf2_km_s, 5),
        published_km_s=published_km_s,
        abs_diff_km_s=round(abs_diff, 5),
        rel_diff_pct=round(rel_diff, 3),
        tolerance_km_s=tolerance_km_s,
        passed=passed,
        definitional_gap_km_s=round(def_gap, 5),
        citation=citation,
    )


def print_arrival_result(result: "ArrivalResult", manifest=None,
                         sample: str = "") -> None:
    """
    Print one arrival-sample comparison row, target-relative frame.

    Manifest-bound. `sample` is "a" or "b" and selects the entry prefix; it is
    inferred from the label when not given.
    """
    if not sample:
        sample = "b" if "Sample B" in result.sample_label else "a"
    if manifest is None:
        from solver.manifest import Manifest, _arrival_entries
        manifest = Manifest(producer="validate",
                            entries=_arrival_entries(result, sample))
    b = f"validate.arrival_{sample}"
    c = manifest.canonical
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"ARRIVAL VELOCITY | {result.sample_label}  [ASSERTED]")
    print(f"  Epoch:          launch JD {c(b + '.launch.jd')}  "
          f"arrival JD {c(b + '.arrival.jd')}")
    print(f"  TOF:            {c(b + '.tof_days')} days  "
          f"({c(b + '.tof_years')} yr)")
    print(f"  Encounter dist: {c(b + '.encounter_distance_au')} AU")
    print(f"  v_inf2 (eq.4):  {c(b + '.v_inf2')} km/s  "
          f"(asymptotic, compared to published)")
    print(f"  v_arr (local):  {c(b + '.v_arr_local')} km/s  "
          f"(HITS native local encounter)")
    print(f"  def. gap:       {c(b + '.definitional_gap')} km/s  "
          f"(|v_inf2 - v_arr|; hyperbolic geometry, not error)")
    print(f"  published:      {c(b + '.published')} km/s  ({result.citation})")
    print(f"  abs diff:       {c(b + '.abs_diff')} km/s  (v_inf2 vs published)")
    print(f"  rel diff:       {c(b + '.rel_diff_pct')}%")
    print(f"  tolerance:      {c(b + '.tolerance')} km/s")
    print(f"  {status}")
    print(f"  {result.fidelity_note}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# C3 grid construction — Fig. 1 axes
# ---------------------------------------------------------------------------

# Fig. 1 duration axis: 5 to 30 years, 1-year step.
C3_GRID_TOF_YEARS_START = 5.0
C3_GRID_TOF_YEARS_STOP = 31.0     # exclusive; yields 5..30
C3_GRID_TOF_YEARS_STEP = 1.0
# Arrival-state lookup tolerance: half the committed 14-day window step.
C3_GRID_ARRIVAL_MATCH_TOL_DAYS = 8.0


def build_c3_grid(earth_svs, oumuamua_svs) -> GridResult:
    """
    Build the C3 porkchop grid over Fig. 1 axes.

    Launch: earth_c3_grid, 2018-2032, 14-day step (391 epochs).
    Duration: 5 to 30 years, 1-year step (26 TOF values).
    Roughly 391 x 26 = 10,166 Lambert solves.

    Arrival lookup: nearest committed 'Oumuamua state (14-day step). A cell is
    left NaN if the nearest state is more than half a step away, so no cell is
    ever solved against an arrival epoch it does not actually have a state for.

    This lived in tests/test_validation.py as a fixture during Phase 1. It moves
    here because the manifest emitter and the judges endpoint need the same grid
    the test suite asserts against, and CLAUDE.md requires that code to exist
    once. The logic is unchanged: the grid it returns is bit-identical to the
    Phase 1 fixture's.
    """
    oumu_jds = np.array([sv.epoch_tdb_jd for sv in oumuamua_svs])

    tof_array = np.arange(
        C3_GRID_TOF_YEARS_START,
        C3_GRID_TOF_YEARS_STOP,
        C3_GRID_TOF_YEARS_STEP,
    ) * 365.25

    n_dep = len(earth_svs)
    n_tof = len(tof_array)

    c3_grid = np.full((n_dep, n_tof), np.nan)
    v_arr_grid = np.full((n_dep, n_tof), np.nan)
    dep_jds = np.array([sv.epoch_tdb_jd for sv in earth_svs])

    for i, earth_sv in enumerate(earth_svs):
        for j, tof in enumerate(tof_array):
            arrival_jd = earth_sv.epoch_tdb_jd + tof
            idx = int(np.argmin(np.abs(oumu_jds - arrival_jd)))
            if abs(oumu_jds[idx] - arrival_jd) > C3_GRID_ARRIVAL_MATCH_TOL_DAYS:
                continue  # no committed state within half the 14-day step
            target_sv = oumuamua_svs[idx]
            try:
                result = solve(earth_sv, target_sv, float(tof))
                c3_grid[i, j] = result.c3_km2_s2
                v_arr_grid[i, j] = result.v_arr_km_s
            except Exception:
                # Collinear or non-convergent: leave as NaN
                pass

    return GridResult(
        c3_grid=c3_grid,
        v_arr_grid=v_arr_grid,
        departure_jds=dep_jds,
        tof_days=tof_array,
    )


# ---------------------------------------------------------------------------
# Top-level validate() — all five quantities, frame gate first
# ---------------------------------------------------------------------------

@dataclass
class ValidationResults:
    """
    Every result the Phase 1 validation produces, in one object.

    The manifest emitter reads this and nothing deeper. It never reaches past
    the public surface into Lambert (CONVENTIONS.md, Public surface).

    c3, arrival_a and arrival_b are None if the frame gate failed, because the
    frame gate is a prerequisite: a wrong frame makes every downstream
    comparison meaningless rather than merely inaccurate.
    """
    frame_gate: FrameGateResult
    c3: Optional[C3Result] = None
    arrival_a: Optional[ArrivalResult] = None
    arrival_b: Optional[ArrivalResult] = None
    grid_result: Optional[GridResult] = None
    retrieval_date: str = ""
    manifest: Optional[object] = None   # solver.manifest.Manifest

    @property
    def all_passed(self) -> bool:
        if not self.frame_gate.passed:
            return False
        if self.c3 is None or self.arrival_a is None or self.arrival_b is None:
            return False
        return (
            self.c3.c3_2027_passed
            and self.c3.c3_floor_passed
            and self.arrival_a.passed
            and self.arrival_b.passed
        )


def validate(state_vectors: dict, lyra_constants: Optional[dict] = None,
             verbose: bool = True) -> ValidationResults:
    """
    Run the full Phase 1 validation suite: all five Lyra comparisons.

    Offline and deterministic. Reads committed state vectors only; makes no
    Horizons call.

    Ordering is a guarantee, not a convenience. The frame gate runs first and
    is pass/fail. If it fails, C3 and both arrival samples are skipped and left
    None, because a frame error invalidates them rather than perturbing them.

    Parameters
    ----------
    state_vectors : dict
        Loaded data/state_vectors.json (solver.fetch.load_state_vectors).
    lyra_constants : dict, optional
        Published targets. Defaults to solver.lyra.LYRA_CONSTANTS.
    verbose : bool
        Print the comparison rows. The printed rows are themselves grounded
        against the manifest by tests/test_groundedness.py.

    Returns
    -------
    ValidationResults
    """
    from solver.lyra import LYRA_CONSTANTS
    from solver.manifest import from_validation_results

    if lyra_constants is None:
        lyra_constants = LYRA_CONSTANTS

    # 1. Frame gate (heliocentric) — must pass first
    fg = validate_frame_gate(
        state_vectors["oumuamua_perihelion"],
        published_km_s=lyra_constants["v_inf_helio_km_s"]["value"],
        tolerance_km_s=lyra_constants["v_inf_helio_km_s"]["tolerance_km_s"],
        citation=lyra_constants["v_inf_helio_km_s"]["citation"],
    )
    if not fg.passed:
        partial = ValidationResults(frame_gate=fg)
        partial.manifest = from_validation_results(partial, inputs=_manifest_inputs(state_vectors))
        if verbose:
            print_frame_gate(fg, partial.manifest)
            print("\nFRAME GATE FAILED. C3 and arrival validation skipped.")
        return partial

    retrieval_date = state_vectors["earth_c3_grid"][0].retrieved_utc

    # 2. Departure C3 (Earth-relative)
    grid_result = build_c3_grid(
        state_vectors["earth_c3_grid"],
        state_vectors["oumuamua_c3_grid"],
    )
    c3 = validate_c3(
        grid_result,
        c3_2027_published=lyra_constants["c3_2027_km2_s2"]["value"],
        c3_2027_tolerance_frac=lyra_constants["c3_2027_km2_s2"]["tolerance_frac"],
        c3_2027_citation=lyra_constants["c3_2027_km2_s2"]["citation"],
        c3_floor_published=lyra_constants["c3_floor_km2_s2"]["value"],
        c3_floor_tolerance_frac=lyra_constants["c3_floor_km2_s2"]["tolerance_frac"],
        c3_floor_citation=lyra_constants["c3_floor_km2_s2"]["citation"],
        retrieval_date=retrieval_date,
    )

    # 3. Arrival relative velocity (target-relative), both pinned samples
    sample_a_cfg = lyra_constants["v_arr_sample_a_km_s"]
    arrival_a = validate_arrival(
        state_vectors["earth_sample_ab_launch"],
        state_vectors["oumuamua_sample_a_arrival"],
        float(sample_a_cfg["tof_days"]),
        published_km_s=sample_a_cfg["value"],
        tolerance_km_s=sample_a_cfg["tolerance_km_s"],
        sample_label="Sample A (launch 2017-06-07, ToF 1.0 yr, ~5.85 AU)",
        citation=sample_a_cfg["citation"],
    )

    sample_b_cfg = lyra_constants["v_arr_sample_b_km_s"]
    arrival_b = validate_arrival(
        state_vectors["earth_sample_ab_launch"],
        state_vectors["oumuamua_sample_b_arrival"],
        float(sample_b_cfg["tof_days"]),
        published_km_s=sample_b_cfg["value"],
        tolerance_km_s=sample_b_cfg["tolerance_km_s"],
        sample_label="Sample B (launch 2017-06-07, ToF 20.0 yr, ~115 AU)",
        citation=sample_b_cfg["citation"],
    )

    results = ValidationResults(
        frame_gate=fg,
        c3=c3,
        arrival_a=arrival_a,
        arrival_b=arrival_b,
        grid_result=grid_result,
        retrieval_date=retrieval_date,
    )

    # The manifest is built before anything is printed, and the rows are then
    # printed from it. That ordering is the guarantee in miniature: the set of
    # citable numbers is fixed first, and every number a reader sees is drawn
    # from that set.
    results.manifest = from_validation_results(
        results, inputs=_manifest_inputs(state_vectors))

    if verbose:
        print_frame_gate(fg, results.manifest)
        print_c3_result(c3, results.manifest)
        print_arrival_result(arrival_a, results.manifest, sample="a")
        print_arrival_result(arrival_b, results.manifest, sample="b")

    return results


def _manifest_inputs(state_vectors: dict) -> dict:
    """Header provenance: which committed states this call read, and when they
    were retrieved."""
    inputs = {"state_vectors": {}}
    for key, val in state_vectors.items():
        svs = val if isinstance(val, list) else [val]
        if not svs:
            continue
        inputs["state_vectors"][key] = {
            "n_states": len(svs),
            "epoch_first_jd": svs[0].epoch_tdb_jd,
            "epoch_last_jd": svs[-1].epoch_tdb_jd,
            "retrieved_utc": svs[0].retrieved_utc,
            "frame": svs[0].frame,
            "center": svs[0].center,
        }
    return inputs
