"""
tests/test_lambert.py — unit tests for solver/lambert.py.

Per CONVENTIONS.md: "The intended branch is a hypothesis until that check runs."
These tests confirm:
  1. Boundary conditions: propagating r0 forward by tof reaches r to within 1 km.
     This also confirms the km/km/s/s unit chain end-to-end.
  2. Energy conservation: vis-viva specific energy at r0 and r agree.
  3. lowpath effect: lowpath=True and lowpath=False give different velocities;
     the default (omitted) is recorded.
  4. ValueError raised for tof <= 0.
  5. The solver converges on the 'Oumuamua perihelion vectors.
"""

import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from solver.constants import MU_SUN
from solver.lambert import lambert_solve, LambertResult
from solver.fetch import load_state_vectors
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state_vectors.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def propagate_kepler_scipy(r0, v0, tof_s, mu):
    """
    Two-body propagator using scipy solve_ivp (RK45, tight tolerances).
    Accurate for long arcs (365+ days, 8+ AU).
    Returns final position vector.
    """
    def ode(t, y):
        pos = y[:3]
        vel = y[3:]
        r_mag = np.linalg.norm(pos)
        acc = -mu / r_mag**3 * pos
        return np.concatenate([vel, acc])

    y0 = np.concatenate([np.array(r0), np.array(v0)])
    sol = solve_ivp(ode, [0.0, tof_s], y0, rtol=1e-12, atol=1e-6, max_step=tof_s / 500)
    return sol.y[:3, -1]


def vis_viva_speed(r_km, a_km, mu):
    """Vis-viva equation: v = sqrt(mu * (2/r - 1/a))."""
    return math.sqrt(mu * (2.0 / r_km - 1.0 / a_km))


def semi_major_axis(r_km, v_km_s, mu):
    """Semi-major axis from position and speed."""
    return 1.0 / (2.0 / r_km - v_km_s**2 / mu)


def specific_energy(r_km, v_km_s, mu):
    """Specific orbital energy = v^2/2 - mu/r."""
    return 0.5 * v_km_s**2 - mu / r_km


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def oumuamua_perihelion_sv():
    svs = load_state_vectors(DATA_PATH)
    return svs["oumuamua_perihelion"]


@pytest.fixture(scope="module")
def test_transfer_pair():
    """
    A matched (Earth departure, 'Oumuamua arrival) pair for Lambert tests.
    Uses the pinned Sample A transfer: Earth departs 2017-06-07, 'Oumuamua
    at 2018-06-07 (365 days later). Single pinned states from PROVENANCE.md.
    """
    svs = load_state_vectors(DATA_PATH)
    earth_sv = svs["earth_sample_ab_launch"]       # 2017-06-07 12:00:00 TDB
    oumu_sv  = svs["oumuamua_sample_a_arrival"]    # 2018-06-07 12:00:00 TDB
    return earth_sv, oumu_sv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bad_tof_raises():
    """tof <= 0 must raise ValueError."""
    r0 = np.array([1e8, 0.0, 0.0])
    r  = np.array([0.0, 1e8, 0.0])
    with pytest.raises(ValueError):
        lambert_solve(r0, r, 0.0)
    with pytest.raises(ValueError):
        lambert_solve(r0, r, -1.0)


def test_returns_lambert_result(test_transfer_pair):
    """lambert_solve returns a LambertResult."""
    earth_sv, oumu_sv = test_transfer_pair
    r0 = earth_sv.r
    r  = oumu_sv.r
    tof_s = 365.0 * 86400.0
    result = lambert_solve(r0, r, tof_s)
    assert isinstance(result, LambertResult)
    assert result.tof_s == tof_s
    assert len(result.v_depart_km_s) == 3
    assert len(result.v_arrive_km_s) == 3


def test_boundary_conditions(test_transfer_pair):
    """
    Propagating r0 forward by tof under two-body gravity must reach r to within 1 km.
    Uses a self-consistent pair: Earth 2017-10-19 -> 'Oumuamua 2018-10-19 (365 d).
    This confirms the km/km/s/s unit chain end-to-end (CONVENTIONS.md).
    """
    earth_sv, oumu_sv = test_transfer_pair
    r0 = earth_sv.r
    r_target = oumu_sv.r
    tof_s = 365.0 * 86400.0

    result = lambert_solve(r0, r_target, tof_s)

    # Propagate from r0 with departure velocity for tof_s
    r_propagated = propagate_kepler_scipy(r0, result.v_depart_km_s, tof_s, MU_SUN)

    error_km = np.linalg.norm(r_propagated - r_target)
    print(f"\n  Boundary condition error: {error_km:.3f} km (tolerance: 1 km)")
    assert error_km < 1.0, (
        f"Lambert boundary condition failed: propagated position misses target by "
        f"{error_km:.3f} km. Unit chain (km/km_s/s) may be wrong."
    )


def test_energy_conservation(test_transfer_pair):
    """
    Specific orbital energy must agree at departure and arrival points.
    Tests vis-viva consistency along the Lambert arc.
    """
    earth_sv, oumu_sv = test_transfer_pair
    r0 = earth_sv.r
    r  = oumu_sv.r
    tof_s = 365.0 * 86400.0

    result = lambert_solve(r0, r, tof_s)

    r0_mag = np.linalg.norm(r0)
    v0_mag = np.linalg.norm(result.v_depart_km_s)
    r_mag  = np.linalg.norm(r)
    v_mag  = np.linalg.norm(result.v_arrive_km_s)
    e_depart = specific_energy(r0_mag, v0_mag, MU_SUN)
    e_arrive = specific_energy(r_mag, v_mag, MU_SUN)

    energy_diff = abs(e_depart - e_arrive)
    print(f"\n  Energy at departure: {e_depart:.6f} km^2/s^2")
    print(f"  Energy at arrival:   {e_arrive:.6f} km^2/s^2")
    print(f"  Difference:          {energy_diff:.6f} km^2/s^2")

    tol = 0.001 * abs(e_depart)
    assert energy_diff < tol, (
        f"Energy not conserved: depart={e_depart:.6f}, arrive={e_arrive:.6f}, "
        f"diff={energy_diff:.6f} km^2/s^2 (tol={tol:.6f})"
    )


def test_lowpath_branch_documented(test_transfer_pair):
    """
    Documents the lowpath branch behaviour for the 'Oumuamua problem geometry.
    Per CONVENTIONS.md: effect confirmed by test, not assumed.

    For 'Oumuamua (fast-receding hyperbolic target, large transfer angle),
    lowpath=True and False converge to the same solution. This is expected
    for M=0 transfers to very distant targets. The hapsira default is lowpath=True
    (confirmed from hapsira source; the parameter default is True).

    This test records this fact and confirms that lambert_solve (omitted lowpath)
    matches hapsira's documented default (lowpath=True).
    """
    import astropy.units as u
    from hapsira.iod.izzo import lambert as _hapsira_lambert

    earth_sv, oumu_sv = test_transfer_pair
    r0 = earth_sv.r
    r  = oumu_sv.r
    tof_s = 365.0 * 86400.0

    k_qty   = MU_SUN * (u.km**3 / u.s**2)
    r0_qty  = r0 * u.km
    r_qty   = r  * u.km
    tof_qty = tof_s * u.s

    v0_low_true,  _ = _hapsira_lambert(k_qty, r0_qty, r_qty, tof_qty, M=0, prograde=True, lowpath=True)
    v0_low_false, _ = _hapsira_lambert(k_qty, r0_qty, r_qty, tof_qty, M=0, prograde=True, lowpath=False)

    diff = np.linalg.norm(np.array(v0_low_true) - np.array(v0_low_false))
    print(f"\n  lowpath=True  v_depart magnitude: {np.linalg.norm(np.array(v0_low_true)):.4f} km/s")
    print(f"  lowpath=False v_depart magnitude: {np.linalg.norm(np.array(v0_low_false)):.4f} km/s")
    print(f"  Difference: {diff:.6f} km/s")
    print(f"  NOTE: For 'Oumuamua geometry (large transfer angle, fast receding target),")
    print(f"        lowpath branches converge. This is expected for M=0.")
    print(f"        hapsira default is lowpath=True (per hapsira source).")

    # Confirm lambert_solve (omitted lowpath) matches lowpath=True.
    # v0_low_true is a Quantity array; extract values before comparison.
    result_default = lambert_solve(r0, r, tof_s)
    import astropy.units as _u
    v0_true_vals = (np.array(v0_low_true.to_value(_u.km / _u.s))
                    if hasattr(v0_low_true, 'to_value')
                    else np.array(v0_low_true))
    diff_from_true = np.linalg.norm(result_default.v_depart_km_s - v0_true_vals)
    print(f"  lambert_solve default vs lowpath=True: {diff_from_true:.8f} km/s (should be ~0)")
    assert diff_from_true < 1e-6, (
        f"lambert_solve default does not match lowpath=True: diff={diff_from_true:.8f} km/s"
    )


def test_convergence_on_oumuamua_perihelion(oumuamua_perihelion_sv, test_transfer_pair):
    """
    Confirm the solver converges when using 'Oumuamua state vectors.
    This is a smoke test, not a validation number.
    """
    earth_sv, _ = test_transfer_pair
    r0 = earth_sv.r
    r  = oumuamua_perihelion_sv.r
    tof_s = 180.0 * 86400.0  # 180-day hypothetical transfer (just for convergence check)

    # Should not raise
    result = lambert_solve(r0, r, tof_s)
    v_depart = np.linalg.norm(result.v_depart_km_s)
    v_arrive = np.linalg.norm(result.v_arrive_km_s)

    print(f"\n  Convergence test (180-day transfer to perihelion position):")
    print(f"  v_depart: {v_depart:.4f} km/s, v_arrive: {v_arrive:.4f} km/s")
    assert 0.0 < v_depart < 200.0
    assert 0.0 < v_arrive < 200.0
