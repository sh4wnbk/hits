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
# Lyra validation constants
# ---------------------------------------------------------------------------
# These moved to solver/lyra.py in Phase 2. The manifest emitter and the judges
# endpoints need them, and they cannot live in a test-only module if the same
# code is to prove the claim in CI and in a browser (CLAUDE.md, "Write the
# validation once"). Re-exported here so existing fixtures keep working.

from solver.lyra import LYRA_CONSTANTS  # noqa: E402


@pytest.fixture(scope="session")
def lyra_constants():
    """Lyra published validation targets. All citations from Hein et al. 2019."""
    return LYRA_CONSTANTS
