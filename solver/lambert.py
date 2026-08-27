"""
solver/lambert.py — thin wrapper over hapsira.iod.izzo.lambert.

Per CONVENTIONS.md (hapsira scope):
  Call: hapsira.iod.izzo.lambert(k, r0, r, tof)
  Units: k in km^3/s^2, positions in km, tof in seconds
  Returns: (v0, v) velocity pair in km/s

Note on unit handling: hapsira.iod.izzo.lambert internally calls
.to_value() on its arguments, so they must be passed as astropy
Quantity objects with the correct units attached. This wrapper
attaches units immediately before the call and strips them from the
result, keeping all HITS internals as plain numpy floats/arrays in
km and km/s. The astropy unit attachment is a call-site adapter only;
HITS state vectors are always plain km/km_s throughout.

Per CONVENTIONS.md (Lambert branch selection):
  M=0 (zero revolutions), prograde=True.
  lowpath is NOT set here; it is left at the hapsira default.
  Its effect is confirmed by the boundary test in test_lambert.py,
  not assumed. The intended branch is a hypothesis until that test runs.

k is imported from solver.constants, never redefined locally.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import astropy.units as u
from hapsira.iod.izzo import lambert as _hapsira_lambert

from solver.constants import MU_SUN


@dataclass
class LambertResult:
    """
    Result of a Lambert solve.
    All velocities in km/s. tof in seconds.
    """
    v_depart_km_s: np.ndarray   # departure velocity vector (km/s)
    v_arrive_km_s: np.ndarray   # arrival velocity vector (km/s)
    tof_s: float                # time of flight (seconds)


def lambert_solve(
    r0: np.ndarray,
    r: np.ndarray,
    tof_s: float,
    k: float = MU_SUN,
) -> LambertResult:
    """
    Solve the Lambert problem between two position vectors.

    Parameters
    ----------
    r0 : np.ndarray
        Departure position vector, km, ECLIPJ2000 heliocentric.
    r : np.ndarray
        Arrival position vector, km, ECLIPJ2000 heliocentric.
    tof_s : float
        Time of flight in seconds (positive).
    k : float
        Gravitational parameter in km^3/s^2. Default: MU_SUN from constants.
        Never pass a literal here; import MU_SUN instead.

    Returns
    -------
    LambertResult
        v_depart_km_s, v_arrive_km_s (both in km/s), tof_s.

    Raises
    ------
    ValueError
        If tof_s <= 0.
    """
    if tof_s <= 0.0:
        raise ValueError(f"tof_s must be positive, got {tof_s}")

    # hapsira.iod.izzo.lambert requires astropy Quantity inputs (calls .to_value()).
    # Attach units here at the call boundary; strip them from the result.
    # HITS internals remain plain floats/arrays in km and km/s throughout.
    k_qty   = k * (u.km**3 / u.s**2)
    r0_qty  = np.array(r0) * u.km
    r_qty   = np.array(r)  * u.km
    tof_qty = tof_s * u.s

    # Call hapsira with M=0 (direct), prograde=True.
    # lowpath is NOT set; left at hapsira's default.
    # Confirmed by test_lambert.py::test_lowpath_effect.
    v0_qty, v_qty = _hapsira_lambert(
        k_qty,
        r0_qty,
        r_qty,
        tof_qty,
        M=0,
        prograde=True,
        # lowpath: deliberately omitted — default confirmed by boundary test
    )

    # Strip units; return plain arrays in km/s
    v0 = v0_qty.to_value(u.km / u.s)
    v  = v_qty.to_value(u.km / u.s)

    return LambertResult(
        v_depart_km_s=np.array(v0),
        v_arrive_km_s=np.array(v),
        tof_s=tof_s,
    )
