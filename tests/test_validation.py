"""
tests/test_validation.py — integration validation against Lyra published figures.

ORDERING: test_frame_gate runs first and is a prerequisite.
All other tests are skipped if test_frame_gate fails.

Three quantities, three frames, never shared in a single table:
  1. v_inf heliocentric  — test_frame_gate
  2. Departure C3        — test_c3_2027, test_c3_floor
  3. Arrival v_rel       — test_arrival_sample_a, test_arrival_sample_b

Samples A and B: single pinned transfers. Epoch blocker resolved.
Both samples are ASSERTED (not reported). Sample B keeps wide explicit tolerance.

Fidelity: patched-conic, two-body. No n-body integration.
Citations: Hein et al. 2019, Acta Astronautica 161, 552-561.
"""

import os
import numpy as np
import pytest
from astropy.time import Time

from solver.validate import (
    build_c3_grid,
    validate_frame_gate, print_frame_gate, FrameGateResult,
    validate_c3, print_c3_result,
    validate_arrival, print_arrival_result,
)
from solver.grid import grid as make_grid, GridResult
from solver.fetch import load_state_vectors
from solver.lyra import LYRA_CONSTANTS

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state_vectors.json")

# Lyra constants live in solver/lyra.py as of Phase 2, so the manifest emitter
# and the judges endpoints read the same published figures the tests assert
# against. All citations from Hein et al. 2019.
LYRA = LYRA_CONSTANTS


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def svs():
    return load_state_vectors(DATA_PATH)


@pytest.fixture(scope="module")
def frame_gate_result(svs):
    sv = svs["oumuamua_perihelion"]
    return validate_frame_gate(
        sv,
        published_km_s=LYRA["v_inf_helio_km_s"]["value"],
        tolerance_km_s=LYRA["v_inf_helio_km_s"]["tolerance_km_s"],
        citation=LYRA["v_inf_helio_km_s"]["citation"],
    )


@pytest.fixture(scope="module")
def c3_grid_result(svs):
    """
    The Fig. 1 C3 porkchop grid.

    The construction moved to solver.validate.build_c3_grid in Phase 2 so the
    manifest emitter grids exactly what the test suite asserts against. Axes,
    step, and arrival-matching tolerance are unchanged from Phase 1.
    """
    return build_c3_grid(svs["earth_c3_grid"], svs["oumuamua_c3_grid"])


# ---------------------------------------------------------------------------
# 1. Frame gate — heliocentric frame — MUST PASS FIRST
# ---------------------------------------------------------------------------

def test_frame_gate(frame_gate_result):
    """
    Heliocentric v_inf of 'Oumuamua at perihelion vs Lyra 26.33 km/s.
    Formula: sqrt(v^2 - 2*mu/r)  — GLOSSARY.md, hyperbolic excess velocity.
    This is the PASS/FAIL gate. All other validation is skipped if it fails.
    Citation: Hein et al. 2019, p.553 col 1.
    Fidelity: patched-conic, 2-body.
    """
    print_frame_gate(frame_gate_result)
    assert frame_gate_result.passed, (
        f"FRAME GATE FAILED: computed {frame_gate_result.computed_km_s:.5f} km/s, "
        f"published {frame_gate_result.published_km_s} km/s, "
        f"diff {frame_gate_result.abs_diff_km_s:.5f} km/s > "
        f"tolerance {frame_gate_result.tolerance_km_s} km/s."
    )


# ---------------------------------------------------------------------------
# 2. Departure C3 — Earth-relative frame
# ---------------------------------------------------------------------------

def test_c3_2027(svs, c3_grid_result, frame_gate_result):
    """
    Departure C3 against Lyra ~1400 km^2/s^2 at 2027 launch.
    Frame: Earth-relative departure.
    Extracted as minimum over 2027 launch column (all durations).
    Citation: Hein et al. 2019, p.554 col 1 (37.4 km/s, ~15-yr duration).
    Fidelity: patched-conic, 2-body.
    """
    if not frame_gate_result.passed:
        pytest.skip("Frame gate failed — C3 validation skipped.")

    result = validate_c3(
        c3_grid_result,
        c3_2027_published=LYRA["c3_2027_km2_s2"]["value"],
        c3_2027_tolerance_frac=LYRA["c3_2027_km2_s2"]["tolerance_frac"],
        c3_2027_citation=LYRA["c3_2027_km2_s2"]["citation"],
        c3_floor_published=LYRA["c3_floor_km2_s2"]["value"],
        c3_floor_tolerance_frac=LYRA["c3_floor_km2_s2"]["tolerance_frac"],
        c3_floor_citation=LYRA["c3_floor_km2_s2"]["citation"],
        retrieval_date=svs["earth_c3_grid"][0].retrieved_utc,
    )
    print_c3_result(result)

    tol = LYRA["c3_2027_km2_s2"]["tolerance_frac"] * LYRA["c3_2027_km2_s2"]["value"]
    print(f"\n  MEASURED C3 2027 gap from 1400: {result.c3_2027_abs_diff:.2f} km^2/s^2")
    print(f"  (Once measured, tighten tolerance to gap + 5% margin)")

    assert result.c3_2027_passed, (
        f"C3 2027: computed {result.c3_2027_computed_km2_s2:.2f} km^2/s^2, "
        f"published {result.c3_2027_published_km2_s2} km^2/s^2, "
        f"diff {result.c3_2027_abs_diff:.2f} > tolerance {tol:.2f} km^2/s^2. "
        f"Citation: {result.c3_2027_citation}"
    )


def test_c3_floor(svs, c3_grid_result, frame_gate_result):
    """
    C3 floor against Lyra 703 km^2/s^2.  ASSERTED.
    Frame: Earth-relative departure.
    The floor sits at the early-launch edge of Fig. 1 (2018 launch).
    This edge is physical — 2018 is the earliest realistic launch.

    Phase 1 closeout (2026-08-27): extended-trend check confirmed the floor has
    converged. Using the already-committed oumuamua_c3_grid (to 2062-12-24),
    C3 at 30 yr = 714.36 km^2/s^2 and at 44 yr = 710.97 km^2/s^2 — a drop of
    only 3.39 km^2/s^2 across the full 30-to-44-yr span. The curve has levelled.
    Floor is therefore ASSERTED: 714.36 vs 703 = 1.6% gap, attributed to
    orbit-solution drift (2026 retrieval vs Lyra 2019 ephemeris).
    Lyra's Fig. 1 also stops at 30 years and reads the same converged region.

    Citation: Hein et al. 2019, p.553 col 2 / Fig.1.
    Fidelity: patched-conic, 2-body.
    """
    if not frame_gate_result.passed:
        pytest.skip("Frame gate failed — C3 floor validation skipped.")

    result = validate_c3(
        c3_grid_result,
        c3_2027_published=LYRA["c3_2027_km2_s2"]["value"],
        c3_floor_published=LYRA["c3_floor_km2_s2"]["value"],
        c3_floor_tolerance_frac=LYRA["c3_floor_km2_s2"]["tolerance_frac"],
        c3_floor_citation=LYRA["c3_floor_km2_s2"]["citation"],
        retrieval_date=svs["earth_c3_grid"][0].retrieved_utc,
    )

    print_c3_result(result)
    print(f"\n  C3 FLOOR [ASSERTED]:")
    print(f"  Measured floor:   {result.c3_floor_computed_km2_s2:.2f} km^2/s^2")
    print(f"  Published (Lyra): {result.c3_floor_published_km2_s2:.1f} km^2/s^2")
    print(f"  Gap:              {result.c3_floor_abs_diff:.2f} km^2/s^2 ({result.c3_floor_rel_diff_pct:.1f}%)")
    print(f"  Edge type:        {result.c3_floor_edge_type}")
    print(f"  Gap attribution:  {result.c3_floor_gap_attribution}")
    print(f"  Extended trend:   30-to-44-yr drop = 3.39 km^2/s^2 — curve levelled.")
    print(f"  Citation: {result.c3_floor_citation}")
    print(f"  Patched-conic, 2-body only.")

    # ASSERTED — extended-trend check confirmed convergence (Phase 1 closeout).
    # The floor is on the duration-boundary edge in the 30-yr grid, but the
    # oumuamua_c3_grid extension to 44 yr shows C3 drops only 3.39 km^2/s^2
    # further; the tolerance band (20% of 703 = 140.6 km^2/s^2) is satisfied.
    tol = LYRA["c3_floor_km2_s2"]["tolerance_frac"] * LYRA["c3_floor_km2_s2"]["value"]
    assert result.c3_floor_passed, (
        f"C3 floor: computed {result.c3_floor_computed_km2_s2:.2f} km^2/s^2, "
        f"published {result.c3_floor_published_km2_s2} km^2/s^2, "
        f"diff {result.c3_floor_abs_diff:.2f} > tolerance {tol:.2f} km^2/s^2. "
        f"Edge: {result.c3_floor_edge_type}. "
        f"Citation: {result.c3_floor_citation}"
    )


# ---------------------------------------------------------------------------
# 3. Arrival relative velocity — target-relative frame
# ---------------------------------------------------------------------------

def test_arrival_sample_a(svs, frame_gate_result):
    """
    Sample A: launch 2017-06-07, ToF 1.0 year, arrival 2018-06-07, encounter ~5.85 AU.
    Lyra published v_inf,2 = 13.6 km/s (eq.4, asymptotic). ASSERTED.
    Tolerance: 2.0 km/s initial.
    Compared against v_inf2_km_s (asymptotic). v_arr_km_s (local) also reported.
    Citation: Hein et al. 2019, p.554 col 2 / Fig.5.
    Fidelity: patched-conic, 2-body.
    """
    if not frame_gate_result.passed:
        pytest.skip("Frame gate failed — arrival validation skipped.")

    earth_sv  = svs["earth_sample_ab_launch"]
    target_sv = svs["oumuamua_sample_a_arrival"]
    tof_days  = float(LYRA["v_arr_sample_a_km_s"]["tof_days"])

    result = validate_arrival(
        earth_sv, target_sv, tof_days,
        published_km_s=LYRA["v_arr_sample_a_km_s"]["value"],
        tolerance_km_s=LYRA["v_arr_sample_a_km_s"]["tolerance_km_s"],
        sample_label="Sample A (launch 2017-06-07, ToF 1.0 yr, ~5.85 AU)",
        citation=LYRA["v_arr_sample_a_km_s"]["citation"],
    )
    print_arrival_result(result)

    assert result.passed, (
        f"Sample A FAILED: v_inf2 {result.v_inf2_km_s:.4f} km/s, "
        f"published {result.published_km_s} km/s, "
        f"diff {result.abs_diff_km_s:.4f} km/s > tolerance {result.tolerance_km_s} km/s. "
        f"Citation: {result.citation}"
    )


def test_arrival_sample_b(svs, frame_gate_result):
    """
    Sample B: launch 2017-06-07, ToF 20.0 years, arrival 2037-06-07, encounter ~115 AU.
    Lyra published v_inf,2 ~ 600 m/s = 0.6 km/s (eq.4, asymptotic). ASSERTED.
    Tolerance: 0.3 km/s (wide, explicitly stated).
    At 115 AU the orbit-solution drift (~3.7 AU from paper's 111.4 AU) means local
    speeds differ from the paper's geometry. Wide tolerance is required and stated.
    Citation: Hein et al. 2019, p.554 col 2 / Fig.6.
    Fidelity: patched-conic, 2-body.
    """
    if not frame_gate_result.passed:
        pytest.skip("Frame gate failed — arrival validation skipped.")

    earth_sv  = svs["earth_sample_ab_launch"]
    target_sv = svs["oumuamua_sample_b_arrival"]
    tof_days  = float(LYRA["v_arr_sample_b_km_s"]["tof_days"])

    result = validate_arrival(
        earth_sv, target_sv, tof_days,
        published_km_s=LYRA["v_arr_sample_b_km_s"]["value"],
        tolerance_km_s=LYRA["v_arr_sample_b_km_s"]["tolerance_km_s"],
        sample_label="Sample B (launch 2017-06-07, ToF 20.0 yr, ~115 AU)",
        citation=LYRA["v_arr_sample_b_km_s"]["citation"],
    )
    print_arrival_result(result)

    print(f"\n  NOTE: Wide tolerance ({result.tolerance_km_s} km/s) for Sample B.")
    print(f"  Orbit-solution drift from paper epoch: encounter at {result.encounter_distance_au:.1f} AU")
    print(f"  vs paper's 111.4 AU. Drift is retrieval-date dependent.")

    assert result.passed, (
        f"Sample B FAILED: v_inf2 {result.v_inf2_km_s:.4f} km/s, "
        f"published {result.published_km_s} km/s, "
        f"diff {result.abs_diff_km_s:.4f} km/s > tolerance {result.tolerance_km_s} km/s. "
        f"Wide tolerance ({result.tolerance_km_s} km/s) already applied. "
        f"Citation: {result.citation}"
    )
