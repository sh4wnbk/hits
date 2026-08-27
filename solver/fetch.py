"""
solver/fetch.py — JPL Horizons state-vector retrieval.

Responsibilities (per CONVENTIONS.md):
  - Center: @sun (Sun, not barycenter)
  - Reference plane: ecliptic (ECLIPJ2000)
  - Convert AU -> km and AU/day -> km/s at this boundary, once, nowhere else.
  - Frame confirmation requires two independent checks:
      1. Heliocentric speed (confirms center = Sun)
      2. Out-of-plane velocity component Z or derived inclination
         (confirms plane = ecliptic, not equatorial J2000)

Two modes:
  fetch_state_vector(target, epoch)  — single epoch, returns one StateVector
  fetch_window(target, start, stop)  — daily window, returns list[StateVector]

All downstream code consumes km and km/s only. No AU or AU/day leaves this
module.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List

import numpy as np
from astropy.time import Time
from astroquery.jplhorizons import Horizons

from solver.constants import AU_DAY_TO_KM_S, AU_TO_KM, MU_SUN

# Horizons designation for 'Oumuamua — exact string disambiguates orbit solution.
OUMUAMUA_ID = "1I"  # Horizons designation for 1I/'Oumuamua (confirmed working)
# Sun center code
SUN_CENTER = "@sun"


@dataclass
class StateVector:
    """
    One heliocentric ECLIPJ2000 state at a TDB Julian Date.
    Position in km, velocity in km/s.
    """
    body: str
    role: str
    epoch_tdb_jd: float          # TDB Julian Date
    epoch_iso: str                # ISO 8601 for readability
    frame: str = "ECLIPJ2000"
    center: str = "Sun"
    retrieved_utc: str = ""       # filled at fetch time
    horizons_id: str = ""         # exact Horizons id used
    position_km: List[float] = field(default_factory=list)   # [x, y, z]
    velocity_km_s: List[float] = field(default_factory=list) # [vx, vy, vz]

    @property
    def r(self) -> np.ndarray:
        return np.array(self.position_km)

    @property
    def v(self) -> np.ndarray:
        return np.array(self.velocity_km_s)

    @property
    def speed_km_s(self) -> float:
        return float(np.linalg.norm(self.v))

    @property
    def distance_km(self) -> float:
        return float(np.linalg.norm(self.r))

    def v_inf_helio(self) -> float:
        """
        Heliocentric hyperbolic excess speed (km/s).
        Formula per GLOSSARY.md: v_inf = sqrt(v^2 - 2*mu/r)
        The difference of squares, NOT the difference of speeds.
        """
        v2 = np.dot(self.v, self.v)
        r = self.distance_km
        val = v2 - 2.0 * MU_SUN / r
        if val < 0.0:
            return 0.0  # bound orbit
        return math.sqrt(val)


def _query_horizons(horizons_id: str, epochs) -> object:
    """
    Internal: query Horizons with center=@sun, refplane=ecliptic.
    epochs: single float (JD), list of floats, or dict with start/stop/step.
    """
    obj = Horizons(
        id=horizons_id,
        location=SUN_CENTER,
        epochs=epochs,
    )
    vecs = obj.vectors(refplane="ecliptic")
    return vecs


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_state_vector(horizons_id: str, epoch_tdb_jd: float, role: str = "") -> StateVector:
    """
    Fetch a single heliocentric ECLIPJ2000 state vector from JPL Horizons.

    Parameters
    ----------
    horizons_id : str
        Exact Horizons small-body ID string.
    epoch_tdb_jd : float
        Epoch as a TDB Julian Date.
    role : str
        Human label for this vector (e.g. "self-check (perihelion)").

    Returns
    -------
    StateVector
        Position in km, velocity in km/s, epoch as TDB JD.
    """
    vecs = _query_horizons(horizons_id, epoch_tdb_jd)
    row = vecs[0]

    # Convert from AU / AU/day to km / km/s at this boundary only.
    x  = float(row["x"])  * AU_TO_KM
    y  = float(row["y"])  * AU_TO_KM
    z  = float(row["z"])  * AU_TO_KM
    vx = float(row["vx"]) * AU_DAY_TO_KM_S
    vy = float(row["vy"]) * AU_DAY_TO_KM_S
    vz = float(row["vz"]) * AU_DAY_TO_KM_S

    epoch_iso = Time(epoch_tdb_jd, format="jd", scale="tdb").iso

    return StateVector(
        body=horizons_id,
        role=role,
        epoch_tdb_jd=epoch_tdb_jd,
        epoch_iso=epoch_iso,
        retrieved_utc=_now_utc(),
        horizons_id=horizons_id,
        position_km=[x, y, z],
        velocity_km_s=[vx, vy, vz],
    )


def fetch_window(
    horizons_id: str,
    start_tdb_jd: float,
    stop_tdb_jd: float,
    role: str = "",
    step_days: int = 1,
) -> List[StateVector]:
    """
    Fetch a daily window of heliocentric ECLIPJ2000 state vectors.

    Uses Horizons start/stop/step range query (not a list of JDs) to avoid
    HTTP 414 URI-too-large errors on windows > ~100 epochs.

    Parameters
    ----------
    horizons_id : str
        Exact Horizons id.
    start_tdb_jd, stop_tdb_jd : float
        Window bounds as TDB Julian Dates.
    role : str
        Human label for these vectors.
    step_days : int
        Step size in days (default 1 = daily).

    Returns
    -------
    list[StateVector]
        One entry per day in [start, stop].
    """
    # Horizons range query: start/stop as ISO strings, step as "Nd"
    start_iso = Time(start_tdb_jd, format="jd", scale="tdb").iso.split(".")[0]
    stop_iso  = Time(stop_tdb_jd,  format="jd", scale="tdb").iso.split(".")[0]
    epochs_range = {"start": start_iso, "stop": stop_iso, "step": f"{step_days}d"}
    vecs = _query_horizons(horizons_id, epochs_range)

    results = []
    for row in vecs:
        epoch_jd = float(row["datetime_jd"])
        epoch_iso = Time(epoch_jd, format="jd", scale="tdb").iso

        x  = float(row["x"])  * AU_TO_KM
        y  = float(row["y"])  * AU_TO_KM
        z  = float(row["z"])  * AU_TO_KM
        vx = float(row["vx"]) * AU_DAY_TO_KM_S
        vy = float(row["vy"]) * AU_DAY_TO_KM_S
        vz = float(row["vz"]) * AU_DAY_TO_KM_S

        results.append(StateVector(
            body=horizons_id,
            role=role,
            epoch_tdb_jd=epoch_jd,
            epoch_iso=epoch_iso,
            retrieved_utc=_now_utc(),
            horizons_id=horizons_id,
            position_km=[x, y, z],
            velocity_km_s=[vx, vy, vz],
        ))
    return results


def frame_check(sv: StateVector, expected_speed_km_s: float, expected_incl_deg: float,
                speed_tol: float = 2.0, incl_tol: float = 5.0) -> dict:
    """
    Two-part frame confirmation per CONVENTIONS.md.

    Check 1: heliocentric speed vs expected (confirms center = Sun).
    Check 2: orbital inclination derived from state vs published (confirms plane
             = ecliptic; speed alone cannot distinguish ecliptic from equatorial).

    Inclination from state vector in ECLIPJ2000:
        h = r x v  (angular momentum vector)
        i = arccos(hz / |h|)

    Returns a dict with both checks and pass/fail booleans.
    """
    r = sv.r
    v = sv.v

    # Check 1: heliocentric speed
    speed = sv.speed_km_s
    speed_ok = abs(speed - expected_speed_km_s) <= speed_tol

    # Check 2: inclination from state (ecliptic-plane check)
    h = np.cross(r, v)
    h_mag = np.linalg.norm(h)
    incl_deg = math.degrees(math.acos(np.clip(h[2] / h_mag, -1.0, 1.0)))
    incl_ok = abs(incl_deg - expected_incl_deg) <= incl_tol

    return {
        "heliocentric_speed_km_s": round(speed, 4),
        "expected_speed_km_s": expected_speed_km_s,
        "speed_diff_km_s": round(speed - expected_speed_km_s, 4),
        "speed_ok": speed_ok,
        "inclination_deg": round(incl_deg, 3),
        "expected_incl_deg": expected_incl_deg,
        "incl_diff_deg": round(incl_deg - expected_incl_deg, 3),
        "incl_ok": incl_ok,
        "frame_confirmed": speed_ok and incl_ok,
    }


def save_state_vectors(path: str, entries: dict) -> None:
    """
    Serialize state-vector entries to JSON.

    entries: dict keyed by role string.
      Single-epoch entries: StateVector -> serialized directly.
      Window entries: list[StateVector] -> serialized as list.
    """
    out = {}
    for key, val in entries.items():
        if isinstance(val, list):
            # Window entry: set of daily states
            first = val[0]
            last = val[-1]
            out[key] = {
                "type": "window",
                "body": first.body,
                "role": first.role,
                "window_start_tdb_jd": first.epoch_tdb_jd,
                "window_start_iso": first.epoch_iso,
                "window_end_tdb_jd": last.epoch_tdb_jd,
                "window_end_iso": last.epoch_iso,
                "step_days": 1,
                "n_states": len(val),
                "frame": first.frame,
                "center": first.center,
                "retrieved_utc": first.retrieved_utc,
                "horizons_id": first.horizons_id,
                "states": [
                    {
                        "epoch_tdb_jd": sv.epoch_tdb_jd,
                        "epoch_iso": sv.epoch_iso,
                        "position_km": sv.position_km,
                        "velocity_km_s": sv.velocity_km_s,
                    }
                    for sv in val
                ],
            }
        else:
            # Single-epoch entry
            sv = val
            out[key] = {
                "type": "single",
                "body": sv.body,
                "role": sv.role,
                "epoch_tdb_jd": sv.epoch_tdb_jd,
                "epoch_iso": sv.epoch_iso,
                "frame": sv.frame,
                "center": sv.center,
                "retrieved_utc": sv.retrieved_utc,
                "horizons_id": sv.horizons_id,
                "position_km": sv.position_km,
                "velocity_km_s": sv.velocity_km_s,
            }
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


def load_state_vectors(path: str) -> dict:
    """
    Load state vectors from committed JSON. Returns same structure as save
    produces: keys to either StateVector (single) or list[StateVector] (window).
    """
    with open(path) as f:
        raw = json.load(f)

    result = {}
    for key, entry in raw.items():
        if entry["type"] == "window":
            svs = [
                StateVector(
                    body=entry["body"],
                    role=entry["role"],
                    epoch_tdb_jd=s["epoch_tdb_jd"],
                    epoch_iso=s["epoch_iso"],
                    frame=entry["frame"],
                    center=entry["center"],
                    retrieved_utc=entry["retrieved_utc"],
                    horizons_id=entry["horizons_id"],
                    position_km=s["position_km"],
                    velocity_km_s=s["velocity_km_s"],
                )
                for s in entry["states"]
            ]
            result[key] = svs
        else:
            result[key] = StateVector(
                body=entry["body"],
                role=entry["role"],
                epoch_tdb_jd=entry["epoch_tdb_jd"],
                epoch_iso=entry["epoch_iso"],
                frame=entry["frame"],
                center=entry["center"],
                retrieved_utc=entry["retrieved_utc"],
                horizons_id=entry["horizons_id"],
                position_km=entry["position_km"],
                velocity_km_s=entry["velocity_km_s"],
            )
    return result
