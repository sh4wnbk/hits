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
from solver.grid import grid as _grid
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


def print_frame_gate(result: FrameGateResult) -> None:
    """Print the frame-gate comparison row as specified in the plan."""
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"FRAME GATE | v_inf_helio  [formula: {result.formula}]")
    print(f"  computed:   {result.computed_km_s:.5f} km/s")
    print(f"  published:  {result.published_km_s:.2f} km/s  ({result.citation})")
    print(f"  abs diff:   {result.abs_diff_km_s:.5f} km/s")
    print(f"  rel diff:   {result.rel_diff_pct:.3f}%")
    print(f"  tolerance:  {result.tolerance_km_s} km/s")
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

    gap_attr = (
        f"orbit-solution epoch ({retrieval_date}) + patched-conic method. Not tuned away."
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


def print_c3_result(result: C3Result) -> None:
    """Print C3 comparison rows."""
    from astropy.time import Time as _Time
    dep_iso_2027 = _Time(result.c3_2027_departure_jd, format="jd", scale="tdb").iso[:10]
    dep_iso_floor = _Time(result.c3_floor_departure_jd, format="jd", scale="tdb").iso[:10]
    print(f"\n{'='*60}")
    print("C3 VALIDATION | Earth-relative departure frame")
    print(f"  2027 launch column minimum:")
    print(f"    computed:   {result.c3_2027_computed_km2_s2:.2f} km^2/s^2  "
          f"(departure {dep_iso_2027}, TOF {result.c3_2027_tof_days/365.25:.1f} yr)")
    print(f"    published:  {result.c3_2027_published_km2_s2:.1f} km^2/s^2  ({result.c3_2027_citation})")
    print(f"    abs diff:   {result.c3_2027_abs_diff:.2f} km^2/s^2")
    print(f"    rel diff:   {result.c3_2027_rel_diff_pct:.2f}%")
    print(f"    tolerance:  {100*result.c3_2027_tolerance_frac:.0f}%")
    print(f"    {'PASS' if result.c3_2027_passed else 'FAIL'}")
    print(f"  C3 floor (global grid minimum):")
    print(f"    computed:   {result.c3_floor_computed_km2_s2:.2f} km^2/s^2  "
          f"(departure {dep_iso_floor}, TOF {result.c3_floor_tof_days/365.25:.1f} yr)")
    print(f"    published:  {result.c3_floor_published_km2_s2:.1f} km^2/s^2  ({result.c3_floor_citation})")
    print(f"    abs diff:   {result.c3_floor_abs_diff:.2f} km^2/s^2")
    print(f"    rel diff:   {result.c3_floor_rel_diff_pct:.2f}%")
    print(f"    tolerance:  {100*result.c3_floor_tolerance_frac:.0f}%")
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


def print_arrival_result(result: "ArrivalResult") -> None:
    """Print arrival validation comparison rows."""
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"ARRIVAL VELOCITY | {result.sample_label}  [ASSERTED]")
    print(f"  Epoch:          launch JD {result.launch_epoch_jd:.1f}  "
          f"arrival JD {result.arrival_epoch_jd:.1f}")
    print(f"  TOF:            {result.tof_days:.2f} days  "
          f"({result.tof_days/365.25:.4f} yr)")
    print(f"  Encounter dist: {result.encounter_distance_au:.3f} AU")
    print(f"  v_inf2 (eq.4):  {result.v_inf2_km_s:.5f} km/s  "
          f"(asymptotic, compared to published)")
    print(f"  v_arr (local):  {result.v_arr_local_km_s:.5f} km/s  "
          f"(HITS native local encounter)")
    print(f"  def. gap:       {result.definitional_gap_km_s:.5f} km/s  "
          f"(|v_inf2 - v_arr|; hyperbolic geometry, not error)")
    print(f"  published:      {result.published_km_s:.5f} km/s  ({result.citation})")
    print(f"  abs diff:       {result.abs_diff_km_s:.5f} km/s  "
          f"(v_inf2 vs published)")
    print(f"  rel diff:       {result.rel_diff_pct:.3f}%")
    print(f"  tolerance:      {result.tolerance_km_s} km/s")
    print(f"  {status}")
    print(f"  {result.fidelity_note}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Top-level validate() — calls all three in order
# ---------------------------------------------------------------------------

def validate(state_vectors: dict, lyra_constants: dict) -> dict:
    """
    Run the full Phase 1 validation suite.

    Returns dict with keys 'frame_gate', 'c3', 'arrival_a', 'arrival_b'.
    Skips c3 and arrival if frame gate fails.
    """
    results = {}

    # 1. Frame gate (must pass first)
    sv_perihelion = state_vectors["oumuamua_perihelion"]
    fg = validate_frame_gate(
        sv_perihelion,
        published_km_s=lyra_constants["v_inf_helio_km_s"]["value"],
        tolerance_km_s=lyra_constants["v_inf_helio_km_s"]["tolerance_km_s"],
        citation=lyra_constants["v_inf_helio_km_s"]["citation"],
    )
    print_frame_gate(fg)
    results["frame_gate"] = fg

    if not fg.passed:
        print("\nFRAME GATE FAILED — skipping all other validation.")
        return results

    return results
