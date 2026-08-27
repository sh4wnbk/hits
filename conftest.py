"""
conftest.py — project-wide pytest fixtures.

Fixtures here are available to all test modules.
Phase 1 revision: samples A/B are single pinned states; grid windows updated.
"""

import os
import pytest
from solver.fetch import load_state_vectors

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "state_vectors.json")


@pytest.fixture(scope="session")
def state_vectors():
    """
    Load committed data/state_vectors.json (offline, no Horizons call).
    Available to all test modules. Session-scoped: loaded once per test run.
    """
    assert os.path.exists(DATA_PATH), (
        f"state_vectors.json not found at {DATA_PATH}. "
        "Run data/fetch_pinned.py then data/fetch_c3_grid_new.py first."
    )
    return load_state_vectors(DATA_PATH)


@pytest.fixture(scope="session")
def sv_perihelion(state_vectors):
    """'Oumuamua perihelion state vector (single state)."""
    return state_vectors["oumuamua_perihelion"]


@pytest.fixture(scope="session")
def earth_sample_ab_launch(state_vectors):
    """Earth state at the shared Sample A/B launch epoch (2017-06-07 12:00:00 TDB)."""
    return state_vectors["earth_sample_ab_launch"]


@pytest.fixture(scope="session")
def oumuamua_sample_a_arrival(state_vectors):
    """'Oumuamua state at Sample A arrival epoch (2018-06-07 12:00:00 TDB)."""
    return state_vectors["oumuamua_sample_a_arrival"]


@pytest.fixture(scope="session")
def oumuamua_sample_b_arrival(state_vectors):
    """'Oumuamua state at Sample B arrival epoch (2037-06-07 12:00:00 TDB)."""
    return state_vectors["oumuamua_sample_b_arrival"]


@pytest.fixture(scope="session")
def earth_c3_grid(state_vectors):
    """Earth states over C3 grid launch window (2018-2032, 14-day step)."""
    return state_vectors["earth_c3_grid"]


@pytest.fixture(scope="session")
def oumuamua_c3_grid(state_vectors):
    """'Oumuamua states over C3 grid arrival window (2023-2062, 14-day step)."""
    return state_vectors["oumuamua_c3_grid"]


# ---------------------------------------------------------------------------
# Lyra validation constants — all citations filled from Hein et al. 2019
# ---------------------------------------------------------------------------

LYRA_CONSTANTS = {
    "v_inf_helio_km_s": {
        "value": 26.33,
        "units": "km/s",
        "frame": "heliocentric",
        "tolerance_km_s": 0.5,
        "citation": "Hein et al. 2019, p.553 col 1 / abstract",
    },
    "c3_2027_km2_s2": {
        "value": 1400.0,
        "units": "km^2/s^2",
        "frame": "Earth-relative",
        "tolerance_frac": 0.20,
        "citation": "Hein et al. 2019, p.554 col 1 (37.4 km/s, ~15-yr duration)",
    },
    "c3_floor_km2_s2": {
        "value": 703.0,
        "units": "km^2/s^2",
        "frame": "Earth-relative",
        "tolerance_frac": 0.20,
        "citation": "Hein et al. 2019, p.553 col 2 / Fig.1",
    },
    "v_arr_sample_a_km_s": {
        "value": 13.6,
        "units": "km/s",
        "frame": "target-relative (asymptotic eq.4)",
        "tolerance_km_s": 2.0,
        "citation": "Hein et al. 2019, p.554 col 2 / Fig.5 (eq.4, launch 2017-06-07, ToF 1.0 yr, 5.8 AU)",
        "launch_epoch_tdb": "2017-06-07 12:00:00",
        "arrival_epoch_tdb": "2018-06-07 12:00:00",
        "tof_days": 365.0,
    },
    "v_arr_sample_b_km_s": {
        "value": 0.6,
        "units": "km/s",
        "frame": "target-relative (asymptotic eq.4)",
        "tolerance_km_s": 0.3,
        "citation": "Hein et al. 2019, p.554 col 2 / Fig.6 (eq.4, launch 2017-06-07, ToF 20.0 yr, 111.4 AU)",
        "launch_epoch_tdb": "2017-06-07 12:00:00",
        "arrival_epoch_tdb": "2037-06-07 12:00:00",
        "tof_days": 7305.0,
    },
}


@pytest.fixture(scope="session")
def lyra_constants():
    """Lyra published validation targets. All citations from Hein et al. 2019."""
    return LYRA_CONSTANTS
