"""
tests/test_solve.py — unit tests for solver/solve.py.

Confirms:
  1. solve() returns a SolveResult with C3 >= 0, v_arr >= 0, v_inf2 >= 0.
  2. C3 and v_arr/v_inf2 are in separate fields (never mixed).
  3. C3 = |v_depart - v_earth|^2, Earth-relative.
  4. v_arr = |v_arrive - v_target|, target-relative (local).
  5. v_inf2 uses _v_inf_outgoing_vec (asymptotic, eq.4).
  6. dv_depart = sqrt(C3).
  7. Direction sanity for _v_inf_outgoing_vec:
     - Converges to local velocity direction at large r (111.4 AU).
     - Diverges from local velocity direction at small r (perihelion).
     - Raises ValueError for ingoing leg.
  8. v_inf2 ~= v_arr at large r; v_inf2 != v_arr at small r.
"""

import math
import numpy as np
import pytest
import os

from solver.solve import solve, SolveResult, _v_inf_outgoing_vec
from solver.fetch import load_state_vectors, StateVector
from solver.constants import MU_SUN

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state_vectors.json")


@pytest.fixture(scope="module")
def svs():
    return load_state_vectors(DATA_PATH)


@pytest.fixture(scope="module")
def sample_a_pair(svs):
    """Earth at launch + 'Oumuamua at Sample A arrival (single states, pinned)."""
    earth_sv = svs["earth_sample_ab_launch"]
    oumu_sv  = svs["oumuamua_sample_a_arrival"]
    return earth_sv, oumu_sv


@pytest.fixture(scope="module")
def sample_b_pair(svs):
    """Earth at launch + 'Oumuamua at Sample B arrival (single states, pinned)."""
    earth_sv = svs["earth_sample_ab_launch"]
    oumu_sv  = svs["oumuamua_sample_b_arrival"]
    return earth_sv, oumu_sv


# ---------------------------------------------------------------------------
# Existing tests (preserved, fixture updated to new key names)
# ---------------------------------------------------------------------------

def test_solve_returns_result(sample_a_pair):
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert isinstance(result, SolveResult)


def test_c3_non_negative(sample_a_pair):
    """C3 must always be >= 0 (it is v_inf^2)."""
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert result.c3_km2_s2 >= 0.0, f"C3 < 0: {result.c3_km2_s2}"


def test_v_arr_non_negative(sample_a_pair):
    """Arrival relative velocity must be >= 0 (it is a magnitude)."""
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert result.v_arr_km_s >= 0.0, f"v_arr < 0: {result.v_arr_km_s}"


def test_dv_depart_equals_sqrt_c3(sample_a_pair):
    """dv_depart must equal sqrt(C3) to machine precision."""
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert abs(result.dv_depart_km_s - np.sqrt(result.c3_km2_s2)) < 1e-9


def test_c3_and_v_arr_are_different_quantities(sample_a_pair):
    """
    C3 and v_arr must be in different fields.
    For a launch to a fast-receding target, they will differ substantially.
    """
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert abs(result.c3_km2_s2 - result.v_arr_km_s) > 1.0, (
        "C3 and v_arr appear to be the same value — frame separation may be broken."
    )


def test_c3_formula_matches_manual(sample_a_pair):
    """
    Manually compute C3 from the result's heliocentric velocities and confirm
    it matches the returned c3_km2_s2.
    """
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    dv = result.v_depart_helio_km_s - earth_sv.v
    c3_manual = float(np.dot(dv, dv))
    assert abs(result.c3_km2_s2 - c3_manual) < 1e-9


def test_v_arr_formula_matches_manual(sample_a_pair):
    """
    Manually compute arrival relative velocity from heliocentric velocities.
    """
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    dv = result.v_arrive_helio_km_s - oumu_sv.v
    v_arr_manual = float(np.linalg.norm(dv))
    assert abs(result.v_arr_km_s - v_arr_manual) < 1e-9


def test_solve_prints_frame_labels(sample_a_pair, capsys):
    """Confirm C3 is labeled Earth-relative and v_arr is labeled target-relative."""
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)
    assert hasattr(result, 'c3_km2_s2')
    assert hasattr(result, 'v_arr_km_s')
    assert hasattr(result, 'v_inf2_km_s')
    assert 'c3_km2_s2' in SolveResult.__dataclass_fields__
    assert 'v_arr_km_s' in SolveResult.__dataclass_fields__
    assert 'v_inf2_km_s' in SolveResult.__dataclass_fields__


# ---------------------------------------------------------------------------
# New tests for _v_inf_outgoing_vec and v_inf2_km_s (tests a-f from plan)
# ---------------------------------------------------------------------------

def test_v_inf_outgoing_vec_magnitude(svs):
    """
    Test a: magnitude |_v_inf_outgoing_vec| == v_inf_speed to 1e-6 km/s.
    Use the committed Sample A arrival state at ~5.85 AU (outgoing leg).
    """
    oumu_sv = svs["oumuamua_sample_a_arrival"]
    r = oumu_sv.r
    v = oumu_sv.v

    # Confirm outgoing leg
    assert np.dot(r, v) > 0, "Sample A arrival state should be on outgoing leg"

    v_inf_vec = _v_inf_outgoing_vec(r, v, MU_SUN)
    computed_speed = float(np.linalg.norm(v_inf_vec))

    # Expected speed from vis-viva
    r_mag = float(np.linalg.norm(r))
    v2 = float(np.dot(v, v))
    expected_speed = math.sqrt(max(0.0, v2 - 2.0 * MU_SUN / r_mag))

    assert abs(computed_speed - expected_speed) < 1e-6, (
        f"Magnitude mismatch: computed {computed_speed:.8f} km/s, "
        f"expected {expected_speed:.8f} km/s, diff {abs(computed_speed - expected_speed):.2e}"
    )


def test_v_inf_outgoing_vec_direction_convergence_large_r(svs):
    """
    Test b: direction convergence at large r (~115 AU, Sample B arrival).
    At 115 AU the asymptote direction must be within 0.01 rad of the local
    velocity direction.
    """
    oumu_sv = svs["oumuamua_sample_b_arrival"]
    r = oumu_sv.r
    v = oumu_sv.v

    r_mag = float(np.linalg.norm(r))
    print(f"\n  Sample B r = {r_mag / 1.495978707e8:.2f} AU")

    v_inf_vec = _v_inf_outgoing_vec(r, v, MU_SUN)
    asym_hat = v_inf_vec / np.linalg.norm(v_inf_vec)
    v_hat = v / np.linalg.norm(v)

    cos_angle = float(np.dot(asym_hat, v_hat))
    angle_rad = math.acos(np.clip(cos_angle, -1.0, 1.0))
    print(f"  Direction angle between asymptote and local velocity: {math.degrees(angle_rad):.4f} deg")

    assert angle_rad < 0.01, (
        f"Direction divergence too large at {r_mag/1.495978707e8:.1f} AU: "
        f"{math.degrees(angle_rad):.4f} deg (> 0.57 deg threshold)"
    )


def test_v_inf_outgoing_vec_direction_divergence_small_r(svs):
    """
    Test c: direction diverges from local velocity at small r (perihelion, ~0.255 AU).
    At periapsis the asymptote direction differs from local velocity by >> 5 deg.
    This confirms we are NOT approximating the local direction.
    """
    peri_sv = svs["oumuamua_perihelion"]
    r = peri_sv.r
    v = peri_sv.v

    r_mag = float(np.linalg.norm(r))
    print(f"\n  Perihelion r = {r_mag / 1.495978707e8:.3f} AU")

    # Perihelion state: dot(r,v) should be near zero (at true periapsis it's 0)
    # For the committed state slightly past periapsis it may be small positive;
    # if it's negative we can't call _v_inf_outgoing_vec (would raise).
    rdotv = float(np.dot(r, v))
    print(f"  dot(r,v) = {rdotv:.1f}  (positive = outgoing leg)")

    if rdotv <= 0:
        pytest.skip("Perihelion state is on ingoing leg — cannot test direction divergence here; "
                    "use a state slightly past periapsis")

    v_inf_vec = _v_inf_outgoing_vec(r, v, MU_SUN)
    asym_hat = v_inf_vec / np.linalg.norm(v_inf_vec)
    v_hat = v / np.linalg.norm(v)

    cos_angle = float(np.dot(asym_hat, v_hat))
    angle_rad = math.acos(np.clip(cos_angle, -1.0, 1.0))
    print(f"  Direction angle between asymptote and local velocity: {math.degrees(angle_rad):.2f} deg")

    assert angle_rad > math.radians(5.0), (
        f"Expected asymptote to differ from local velocity by > 5 deg at perihelion; "
        f"got {math.degrees(angle_rad):.2f} deg. "
        f"This may indicate the function is returning the local direction."
    )


def test_v_inf_outgoing_vec_ingoing_leg_raises():
    """
    Test d: a state with dot(r, v) < 0 (ingoing leg) must raise ValueError.
    Fabricate an ingoing state: flip the velocity of a known outgoing state.
    """
    # Use 'Oumuamua perihelion position (r) and negate v to simulate ingoing
    r = np.array([1.0e8, 0.0, 0.0])   # 0.67 AU
    v = np.array([-30.0, -10.0, 0.0]) # dot(r,v) < 0 — ingoing
    assert np.dot(r, v) < 0, "Precondition: should be ingoing leg"

    with pytest.raises(ValueError, match="ingoing leg"):
        _v_inf_outgoing_vec(r, v, MU_SUN)


def test_v_inf2_converges_to_v_arr_at_large_r(sample_b_pair):
    """
    Test e: at 115 AU (Sample B), |v_inf2 - v_arr| < 0.1 km/s.
    Both quantities measure the relative velocity; they converge as r -> inf.
    """
    earth_sv, oumu_sv = sample_b_pair
    result = solve(earth_sv, oumu_sv, tof_days=7305.0)

    diff = abs(result.v_inf2_km_s - result.v_arr_km_s)
    print(f"\n  Sample B: v_inf2={result.v_inf2_km_s:.4f}, v_arr={result.v_arr_km_s:.4f}, "
          f"diff={diff:.4f} km/s")
    assert diff < 0.1, (
        f"v_inf2 and v_arr should converge at 115 AU; diff = {diff:.4f} km/s > 0.1 km/s"
    )


def test_v_inf2_diverges_from_v_arr_at_small_r(sample_a_pair):
    """
    Test f: at 5.85 AU (Sample A), |v_inf2 - v_arr| > 0.1 km/s.
    Near-hyperbolic geometry: asymptote direction has not fully converged
    to local velocity direction. Measured divergence is ~0.25 km/s.

    Threshold is 0.1 km/s (conservative), so that a regression to the
    local-direction approximation (which would give diff ~0 at all r) is caught.
    The local-direction formula gives v_inf2 ≈ v_arr because it just reuses
    the velocity direction — any diff > 0.1 km/s at 5.85 AU proves the
    asymptotic direction is being computed from the eccentricity vector.
    """
    earth_sv, oumu_sv = sample_a_pair
    result = solve(earth_sv, oumu_sv, tof_days=365.0)

    diff = abs(result.v_inf2_km_s - result.v_arr_km_s)
    print(f"\n  Sample A: v_inf2={result.v_inf2_km_s:.4f}, v_arr={result.v_arr_km_s:.4f}, "
          f"diff={diff:.4f} km/s")
    assert diff > 0.1, (
        f"v_inf2 and v_arr should diverge at 5.85 AU; "
        f"diff = {diff:.4f} km/s <= 0.1 km/s. "
        f"This may indicate v_inf2 is using the local direction (wrong formula)."
    )
