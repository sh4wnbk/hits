"""
solver/grid.py — public grid() function.

Per CONVENTIONS.md (Public surface):
  grid(target, departure_range, flight_range) — the C3 and arrival-velocity
  surfaces over the grid.

Vectorises solve() over a departure-epoch index (into committed window arrays)
and a flight-time array. Returns a GridResult with C3 and v_arr as separate
2-D arrays. They are NEVER combined in a single table.

Patched-conic, two-body only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from solver.solve import solve, SolveResult
from solver.fetch import StateVector


@dataclass
class GridResult:
    """
    C3 and v_arr surfaces over departure x TOF grid.

    c3_grid[i, j]   = C3 (km^2/s^2) for departure i, TOF j  — Earth-relative
    v_arr_grid[i, j]= v_arr (km/s) for departure i, TOF j   — target-relative

    These two grids are in different frames. They are never combined.
    departure_jds: TDB JD of each departure epoch (n_departures,)
    tof_days: flight time for each column (n_tofs,)
    """
    c3_grid: np.ndarray      # shape (n_departures, n_tofs),  Earth-relative
    v_arr_grid: np.ndarray   # shape (n_departures, n_tofs),  target-relative
    departure_jds: np.ndarray
    tof_days: np.ndarray

    @property
    def c3_minimum(self):
        """Interior minimum of C3 grid (value, departure_jd, tof_days). Ignores NaN."""
        idx = np.unravel_index(np.nanargmin(self.c3_grid), self.c3_grid.shape)
        return (
            float(self.c3_grid[idx]),
            float(self.departure_jds[idx[0]]),
            float(self.tof_days[idx[1]]),
        )

    def is_c3_minimum_interior(self) -> bool:
        """True if the C3 minimum is not on any grid edge."""
        idx = np.unravel_index(np.nanargmin(self.c3_grid), self.c3_grid.shape)
        i, j = idx
        n_i, n_j = self.c3_grid.shape
        return 0 < i < n_i - 1 and 0 < j < n_j - 1


def grid(
    earth_svs: List[StateVector],
    target_svs: List[StateVector],
    tof_days: np.ndarray,
) -> GridResult:
    """
    Grid the Lambert solver over departure epochs x flight times.

    Parameters
    ----------
    earth_svs : list[StateVector]
        Earth state at each departure epoch. Length = n_departures.
    target_svs : list[StateVector]
        Target state at each *arrival* epoch corresponding to the first
        departure + each TOF value. Length must equal len(earth_svs).
        For a porkchop grid, the caller must supply matched (earth, target)
        pairs for each (departure, TOF) combination.
    tof_days : np.ndarray
        Flight times in days. Shape (n_tofs,).

    Notes on calling pattern for the C3 porkchop slice
    ---------------------------------------------------
    For a C3 slice over departures, call grid() with a single TOF value:
      tof_days = np.array([fixed_tof])
    For a 2-D porkchop, call with multiple TOF values.

    Returns
    -------
    GridResult
    """
    n_dep = len(earth_svs)
    n_tof = len(tof_days)

    c3_grid   = np.full((n_dep, n_tof), np.nan)
    v_arr_grid = np.full((n_dep, n_tof), np.nan)
    departure_jds = np.array([sv.epoch_tdb_jd for sv in earth_svs])

    for i, earth_sv in enumerate(earth_svs):
        for j, tof in enumerate(tof_days):
            # Arrival index: same departure index i, since earth_svs and
            # target_svs are parallel arrays (same window, offset by tof).
            if i < len(target_svs):
                target_sv = target_svs[i]
            else:
                continue
            try:
                result = solve(earth_sv, target_sv, float(tof))
                c3_grid[i, j]    = result.c3_km2_s2
                v_arr_grid[i, j] = result.v_arr_km_s
            except Exception:
                # Collinear or non-convergent: leave as NaN
                pass

    return GridResult(
        c3_grid=c3_grid,
        v_arr_grid=v_arr_grid,
        departure_jds=departure_jds,
        tof_days=np.array(tof_days),
    )
