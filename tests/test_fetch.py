"""
tests/test_fetch.py — unit tests for solver/fetch.py.

Tests run offline using committed data/state_vectors.json.
No Horizons calls are made during testing.
"""

import math
import os
import pytest
import numpy as np

from solver.constants import AU_TO_KM, AU_DAY_TO_KM_S, MU_SUN
from solver.fetch import load_state_vectors, frame_check, StateVector

# Path to the committed state vectors
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state_vectors.json")


@pytest.fixture(scope="module")
def state_vectors():
    """Load committed state_vectors.json (offline, no Horizons call)."""
    assert os.path.exists(DATA_PATH), (
        f"state_vectors.json not found at {DATA_PATH}. "
        "Run data/fetch_and_commit.py first."
    )
    return load_state_vectors(DATA_PATH)


# The six keys the Lyra validation reads (PROVENANCE.md, revision plan v2).
LYRA_KEYS = {
    "oumuamua_perihelion",
    "earth_sample_ab_launch",
    "oumuamua_sample_a_arrival",
    "oumuamua_sample_b_arrival",
    "earth_c3_grid",
    "oumuamua_c3_grid",
}

# The four keys the two unvalidated intercepts read (data/fetch_objects.py).
INTERCEPT_KEYS = {
    "earth_borisov_departure",
    "borisov_arrival",
    "earth_atlas_departure",
    "atlas_arrival",
}


# Every committed entry that is one pinned epoch rather than a window. The two
# intercept objects are single states for the same reason samples A and B are:
# the transfer they belong to is one departure and one arrival, not a search.
SINGLE_STATE_KEYS = (LYRA_KEYS - {"earth_c3_grid", "oumuamua_c3_grid"}) | INTERCEPT_KEYS


def test_json_loads_expected_entries(state_vectors):
    """
    Exactly the Lyra validation keys plus the intercept keys, and nothing else.

    Kept as an equality rather than a subset check on purpose. A committed
    state vector nothing reads is a state vector nobody is checking, and the
    Lyra six have to stay named individually so a later fetch cannot quietly
    drop one and leave the suite green.
    """
    expected_keys = LYRA_KEYS | INTERCEPT_KEYS
    assert set(state_vectors.keys()) == expected_keys, (
        f"Key mismatch.\n  Expected: {sorted(expected_keys)}\n"
        f"  Got:      {sorted(state_vectors.keys())}"
    )


def test_perihelion_is_single_state(state_vectors):
    sv = state_vectors["oumuamua_perihelion"]
    assert isinstance(sv, StateVector)
    assert len(sv.position_km) == 3
    assert len(sv.velocity_km_s) == 3


def test_windows_are_lists(state_vectors):
    """C3 grid windows must be lists of StateVectors."""
    for key in ["earth_c3_grid", "oumuamua_c3_grid"]:
        val = state_vectors[key]
        assert isinstance(val, list), f"{key} should be a list (window entry)"
        assert len(val) > 1, f"{key} window should have multiple states"


def test_single_states_are_not_lists(state_vectors):
    """Pinned single-epoch entries must be StateVector instances, not lists."""
    for key in sorted(SINGLE_STATE_KEYS):
        val = state_vectors[key]
        from solver.fetch import StateVector as _SV
        assert isinstance(val, _SV), f"{key} should be a single StateVector, got {type(val)}"


def test_window_lengths_consistent(state_vectors):
    """C3 grid windows should both have > 100 states (coarse 14-day step)."""
    earth_grid = state_vectors["earth_c3_grid"]
    oumu_grid  = state_vectors["oumuamua_c3_grid"]
    assert len(earth_grid) > 100, f"earth_c3_grid has only {len(earth_grid)} states"
    assert len(oumu_grid)  > 100, f"oumuamua_c3_grid has only {len(oumu_grid)} states"


def test_au_to_km_conversion():
    """AU to km conversion constant matches IAU 2012 exact definition."""
    assert AU_TO_KM == 1.495978707e8


def test_au_day_to_km_s_conversion():
    """AU/day to km/s derived correctly from AU_TO_KM / 86400."""
    expected = 1.495978707e8 / 86400.0
    assert abs(AU_DAY_TO_KM_S - expected) < 1e-6


def test_units_are_km_not_au(state_vectors):
    """Position must be in km (order 1e7-1e9 km), not AU (order 1-10)."""
    sv = state_vectors["oumuamua_perihelion"]
    r = np.linalg.norm(sv.position_km)
    # 0.2 AU < r < 1 AU at perihelion; in km that's ~3e7 to ~1.5e8
    assert r > 1e6, f"Position looks like AU, not km: |r| = {r}"
    assert r < 2e8, f"Position unexpectedly large: |r| = {r} km"


def test_units_are_km_s_not_au_day(state_vectors):
    """Velocity must be in km/s (~87 km/s at perihelion), not AU/day (~0.5 AU/d)."""
    sv = state_vectors["oumuamua_perihelion"]
    v = np.linalg.norm(sv.velocity_km_s)
    assert 50.0 < v < 150.0, f"Velocity looks wrong: |v| = {v} km/s"


def test_frame_check_speed(state_vectors):
    """
    Frame check 1: heliocentric speed at perihelion must be within 2 km/s of ~87.7 km/s.
    This confirms center = Sun (not barycenter).
    Published: Micheli et al. 2018 report ~87.7 km/s heliocentric speed at perihelion.
    Citation: GAP — to be filled when Lyra source is accessed.
    """
    sv = state_vectors["oumuamua_perihelion"]
    speed = sv.speed_km_s
    expected = 87.7
    assert abs(speed - expected) < 2.0, (
        f"Heliocentric speed {speed:.4f} km/s deviates >2 km/s from {expected} km/s. "
        "Frame check (center) failed."
    )


def test_frame_check_inclination(state_vectors):
    """
    Frame check 2: orbital inclination from state must be within 5 deg of ~122 deg.
    This confirms plane = ecliptic (not equatorial J2000).
    Speed alone cannot distinguish ecliptic from equatorial (CONVENTIONS.md).
    Published inclination: ~122.7 deg (ecliptic J2000).
    """
    sv = state_vectors["oumuamua_perihelion"]
    r = sv.r
    v = sv.v
    h = np.cross(r, v)
    h_mag = np.linalg.norm(h)
    incl_deg = math.degrees(math.acos(np.clip(h[2] / h_mag, -1.0, 1.0)))
    expected = 122.0
    assert abs(incl_deg - expected) < 5.0, (
        f"Inclination {incl_deg:.3f} deg deviates >5 deg from {expected} deg. "
        "Frame check (plane) failed."
    )
    print(f"\n  FRAME CHECK: speed={sv.speed_km_s:.4f} km/s, incl={incl_deg:.3f} deg — CONFIRMED")


def test_frame_annotation(state_vectors):
    """Every committed state vector must carry ECLIPJ2000 / Sun annotation."""
    # Single-epoch entries
    for key in sorted(SINGLE_STATE_KEYS):
        sv = state_vectors[key]
        assert sv.frame == "ECLIPJ2000", f"{key}: frame={sv.frame}"
        assert sv.center == "Sun", f"{key}: center={sv.center}"
    # Window entries
    for key in ["earth_c3_grid", "oumuamua_c3_grid"]:
        window = state_vectors[key]
        for sv in window[:3]:  # check first three
            assert sv.frame == "ECLIPJ2000", f"{key}[0-2]: frame={sv.frame}"
            assert sv.center == "Sun", f"{key}[0-2]: center={sv.center}"
