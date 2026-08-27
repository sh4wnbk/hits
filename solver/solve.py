"""
solver/solve.py — public solve() function.

Per CONVENTIONS.md (Public surface):
  solve(target, departure_epoch, flight_time) — one transfer; returns the
  arrival state and the derived departure C3 and arrival relative velocity.

C3 and arrival relative velocity are in SEPARATE fields and SEPARATE frames:
  - departure C3: Earth-relative  (|v_depart - v_earth|^2)
  - arrival v_rel: target-relative  (|v_arrive - v_target|, local)
  - v_inf2: target-relative (asymptotic, eq.4 of Hein et al. 2019)

These quantities are never mixed in a single table.
Patched-conic, two-body only. No n-body integration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from solver.constants import MU_SUN
from solver.lambert import lambert_solve
from solver.fetch import StateVector


def _v_inf_outgoing_vec(r_vec: np.ndarray, v_vec: np.ndarray, mu: float) -> np.ndarray:
    """
    Compute the outgoing asymptotic heliocentric excess velocity vector for a
    body on a hyperbolic orbit around the Sun.

    This is the correct implementation of the asymptotic direction from the
    eccentricity vector and angular momentum. It does NOT approximate the
    asymptote direction using the local velocity direction (that approximation
    is wrong by tens of degrees near periapsis and several degrees at 5.8 AU).

    Derivation (all vectors in 3-D, km and km/s):

      h_vec    = r_vec x v_vec                  (angular momentum)
      e_vec    = (v_vec x h_vec) / mu - r_vec/|r_vec|  (eccentricity, toward periapsis)
      alpha    = arccos(-1 / |e_vec|)           (true anomaly of outgoing asymptote)
      e_hat    = e_vec / |e_vec|                (periapsis direction)
      p_hat    = (h_vec x e_vec) / (|h| |e|)   (in-plane, 90-deg ahead of periapsis)
      asym_hat = cos(alpha)*e_hat + sin(alpha)*p_hat   (outgoing asymptote direction)
      v_inf    = sqrt(max(0, |v|^2 - 2*mu/|r|)) * asym_hat

    Parameters
    ----------
    r_vec : np.ndarray shape (3,) — heliocentric position in km
    v_vec : np.ndarray shape (3,) — heliocentric velocity in km/s
    mu    : float — gravitational parameter in km^3/s^2

    Returns
    -------
    np.ndarray shape (3,) — asymptotic excess velocity vector in km/s

    Raises
    ------
    ValueError
        If dot(r_vec, v_vec) < 0, indicating the body is on the ingoing leg.
        Both 'Oumuamua and the arriving spacecraft must be on the outgoing leg
        at the encounter epoch; this guard catches future misuse.
    """
    r_mag = float(np.linalg.norm(r_vec))
    v2    = float(np.dot(v_vec, v_vec))

    # Outgoing-leg guard
    if float(np.dot(r_vec, v_vec)) < 0.0:
        raise ValueError(
            "ingoing leg: dot(r, v) < 0. _v_inf_outgoing_vec requires the body "
            "to be on the outgoing leg (receding from the Sun). Check the epoch."
        )

    # Bound orbit: return zero vector (not an error; guard against edge cases)
    v_inf_speed = math.sqrt(max(0.0, v2 - 2.0 * mu / r_mag))
    if v_inf_speed == 0.0:
        return np.zeros(3)

    # Angular momentum
    h_vec = np.cross(r_vec, v_vec)
    h_mag = float(np.linalg.norm(h_vec))

    # Eccentricity vector (points toward periapsis, nu = 0)
    e_vec = np.cross(v_vec, h_vec) / mu - r_vec / r_mag
    e_mag = float(np.linalg.norm(e_vec))

    # Asymptote half-angle from periapsis (in pi/2 .. pi for hyperbola, e > 1)
    # arccos(-1/e) is well-defined for e > 1
    cos_alpha = -1.0 / e_mag
    alpha = math.acos(np.clip(cos_alpha, -1.0, 1.0))

    # Unit vectors in the orbital plane
    e_hat = e_vec / e_mag
    # p_hat is the in-plane direction at nu = +90 deg from periapsis
    # p_hat = (h_vec x e_vec) / (|h| * |e|)
    p_hat = np.cross(h_vec, e_vec) / (h_mag * e_mag)

    # Outgoing asymptote direction
    asym_hat = math.cos(alpha) * e_hat + math.sin(alpha) * p_hat

    return v_inf_speed * asym_hat


@dataclass
class SolveResult:
    """
    Result of a single Lambert transfer.

    Fields are kept in their respective frames; they are never combined.
    Fidelity: patched-conic two-body, no n-body integration.

    v_arr_km_s  : HITS native local encounter relative velocity |v_arrive - v_target|.
    v_inf2_km_s : eq.4 of Hein et al. 2019 — magnitude of the vector difference
                  of the two asymptotic heliocentric excess velocities of the
                  spacecraft and the target. This is what the Lyra paper compares
                  against 13.6 km/s (Sample A) and 0.6 km/s (Sample B).
                  Computed from the eccentricity vector, not the local velocity
                  direction. The two fields nearly coincide at 111.4 AU; they
                  differ by several km/s at 5.8 AU due to hyperbolic geometry,
                  not orbit-solution error.
    """
    # Earth-relative departure frame
    c3_km2_s2: float          # departure C3 = |v_depart - v_earth|^2  (km^2/s^2)
    dv_depart_km_s: float     # |v_depart - v_earth| (km/s); sqrt(C3)

    # Target-relative arrival frame — two sub-fields, never combined with C3
    v_arr_km_s: float         # local encounter relative velocity |v_arrive - v_target| (km/s)
    v_inf2_km_s: float        # asymptotic eq.4: |v_inf_SC - v_inf_1I| (km/s)

    # Transfer metadata
    tof_days: float
    departure_epoch_jd: float
    arrival_epoch_jd: float

    # Raw heliocentric velocities (km/s) for downstream use
    v_depart_helio_km_s: np.ndarray   # heliocentric departure velocity
    v_arrive_helio_km_s: np.ndarray   # heliocentric arrival velocity


def solve(
    earth_sv: StateVector,
    target_sv: StateVector,
    tof_days: float,
) -> SolveResult:
    """
    Solve a single Lambert transfer from Earth to target.

    Parameters
    ----------
    earth_sv : StateVector
        Earth state at departure epoch (ECLIPJ2000, km, km/s).
    target_sv : StateVector
        Target state at arrival epoch (ECLIPJ2000, km, km/s).
        Arrival epoch must equal departure epoch + tof_days.
    tof_days : float
        Time of flight in days (positive).

    Returns
    -------
    SolveResult
        C3 in Earth-relative frame; v_arr and v_inf2 in target-relative frame.
        Never mixed.
    """
    tof_s = tof_days * 86400.0

    result = lambert_solve(
        r0=earth_sv.r,
        r=target_sv.r,
        tof_s=tof_s,
    )

    v_depart = result.v_depart_km_s     # heliocentric (km/s)
    v_arrive = result.v_arrive_km_s     # heliocentric (km/s)
    v_earth  = earth_sv.v               # heliocentric Earth velocity (km/s)
    v_target = target_sv.v              # heliocentric target velocity (km/s)

    # Departure C3: Earth-relative frame
    # C3 = |v_spacecraft - v_earth|^2  (GLOSSARY.md: C3, Earth-relative)
    dv_depart_vec = v_depart - v_earth
    c3 = float(np.dot(dv_depart_vec, dv_depart_vec))   # km^2/s^2
    dv_depart = float(np.sqrt(c3))                     # km/s

    # Local arrival relative velocity: target-relative frame
    # v_arr = |v_spacecraft_arrive - v_target|  (GLOSSARY.md: arrival relative velocity)
    dv_arrive_vec = v_arrive - v_target
    v_arr = float(np.linalg.norm(dv_arrive_vec))       # km/s

    # Asymptotic arrival relative velocity: eq.4 of Hein et al. 2019
    # Both bodies are at target_sv.r at the arrival epoch (Lambert constraint).
    # Both must be on the outgoing leg; ValueError raised if not.
    v_inf_sc_vec  = _v_inf_outgoing_vec(target_sv.r, v_arrive,  MU_SUN)
    v_inf_1i_vec  = _v_inf_outgoing_vec(target_sv.r, v_target,  MU_SUN)
    v_inf2 = float(np.linalg.norm(v_inf_sc_vec - v_inf_1i_vec))

    return SolveResult(
        c3_km2_s2=c3,
        dv_depart_km_s=dv_depart,
        v_arr_km_s=v_arr,
        v_inf2_km_s=v_inf2,
        tof_days=tof_days,
        departure_epoch_jd=earth_sv.epoch_tdb_jd,
        arrival_epoch_jd=target_sv.epoch_tdb_jd,
        v_depart_helio_km_s=v_depart,
        v_arrive_helio_km_s=v_arrive,
    )
