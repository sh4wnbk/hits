"""
Baseline: records the pre-existing test and import state of hapsira and astropy
before any HITS solver code is written. Any failure here pre-dates HITS and is
never attributed to it.

Evidence collected 2025-07-13:
  hapsira 0.18.0: no test files in installed wheel (0 collected)
  astropy 8.0.1:  matplotlib 3.7.2 compiled against NumPy 1.x; fails to import
                  under NumPy 2.4.6. This blocks astropy's own test suite from
                  loading because astropy/conftest.py imports matplotlib.
                  Pre-existing; HITS does not use matplotlib (plotting is plotly).

HITS-used modules that import cleanly (verified by _check_imports.py run):
  hapsira.iod.izzo        OK
  hapsira.core.iod        OK
  astropy.constants       OK  (GM_sun = 1.327124e+11 km^3/s^2)
  numpy 2.4.6             OK
  plotly 6.8.0            OK
"""

import pytest


def test_hapsira_iod_izzo_imports():
    """hapsira.iod.izzo.lambert must import and be callable."""
    from hapsira.iod.izzo import lambert
    assert callable(lambert)


def test_hapsira_core_iod_imports():
    """hapsira.core.iod must import cleanly."""
    import hapsira.core.iod  # noqa: F401


def test_astropy_constants_imports():
    """astropy.constants.GM_sun must import and convert to km^3/s^2."""
    from astropy.constants import GM_sun
    gm = GM_sun.to("km3/s2").value
    # Sanity: should be approximately 1.327e11 km^3/s^2
    assert 1.326e11 < gm < 1.328e11, f"GM_sun out of expected range: {gm}"


def test_numpy_version():
    """numpy must be importable. 2.x is in use; matplotlib breakage is pre-existing."""
    import numpy as np
    major = int(np.__version__.split(".")[0])
    assert major >= 1


def test_plotly_imports():
    """plotly must import cleanly (used for C3 slice plot)."""
    import plotly.graph_objects as go  # noqa: F401


@pytest.mark.xfail(
    reason=(
        "PRE-EXISTING and expected to fail two different ways. On the "
        "development host, matplotlib 3.7.2 was compiled against NumPy 1.x "
        "and cannot be imported under NumPy 2.4.6. On a clean install it is "
        "absent entirely: hapsira caps matplotlib below 3.8, no such version "
        "ships a CPython 3.12 wheel that permits NumPy 2, so requirements.txt "
        "omits it and installs with --no-deps. Either way HITS does not use "
        "matplotlib; plotting is plotly. Not caused by HITS."
    ),
    strict=False,
)
def test_matplotlib_numpy2_compat():
    """
    Documents the pre-existing matplotlib/NumPy2 incompatibility.
    Expected to fail; marked xfail so it remains visible but does not block
    the HITS suite.
    """
    import matplotlib  # noqa: F401
