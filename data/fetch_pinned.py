"""
data/fetch_pinned.py — fetch the three pinned single-epoch states for samples A/B.

Per PROVENANCE.md (epoch blocker: resolved):
  Both samples share launch 2017-06-07 12:00:00 TDB.
  Sample A arrives 2018-06-07 12:00:00 TDB  (ToF 1.0 year).
  Sample B arrives 2037-06-07 12:00:00 TDB  (ToF 20.0 years).

The calendar strings are passed to Horizons; the returned JDs are recorded.
No JD is hardcoded here.

Run from project root:
  python data/fetch_pinned.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astropy.time import Time
from solver.fetch import fetch_state_vector, load_state_vectors, save_state_vectors
from solver.constants import AU_TO_KM

DATA_PATH = os.path.join(os.path.dirname(__file__), "state_vectors.json")

# Calendar strings — source of truth; JDs are derived at fetch time.
LAUNCH_TDB_ISO    = "2017-06-07 12:00:00"   # shared launch for A and B
ARRIVAL_A_TDB_ISO = "2018-06-07 12:00:00"   # A: +1.0 year
ARRIVAL_B_TDB_ISO = "2037-06-07 12:00:00"   # B: +20.0 years

def iso_to_jd(iso_str):
    return Time(iso_str, format="iso", scale="tdb").jd

def main():
    print("=== fetch_pinned.py ===")

    # Convert calendar strings to TDB JDs (derived, not hardcoded)
    launch_jd    = iso_to_jd(LAUNCH_TDB_ISO)
    arrival_a_jd = iso_to_jd(ARRIVAL_A_TDB_ISO)
    arrival_b_jd = iso_to_jd(ARRIVAL_B_TDB_ISO)

    print(f"Launch    : {LAUNCH_TDB_ISO} TDB  -> JD {launch_jd}")
    print(f"Arrival A : {ARRIVAL_A_TDB_ISO} TDB  -> JD {arrival_a_jd}")
    print(f"Arrival B : {ARRIVAL_B_TDB_ISO} TDB  -> JD {arrival_b_jd}")

    tof_a_days = arrival_a_jd - launch_jd
    tof_b_days = arrival_b_jd - launch_jd
    print(f"ToF A : {tof_a_days:.4f} days ({tof_a_days/365.25:.4f} yr)")
    print(f"ToF B : {tof_b_days:.4f} days ({tof_b_days/365.25:.4f} yr)")

    # Fetch
    print("\nFetching earth_sample_ab_launch (Earth at launch)...")
    earth_launch = fetch_state_vector("399", launch_jd, role="Sample A/B launch (Earth)")
    print(f"  JD returned: {earth_launch.epoch_tdb_jd}  ISO: {earth_launch.epoch_iso}")
    print(f"  r = {earth_launch.distance_km/AU_TO_KM:.4f} AU  speed = {earth_launch.speed_km_s:.4f} km/s")

    print("Fetching oumuamua_sample_a_arrival (1I at Sample A arrival)...")
    oumu_a = fetch_state_vector("1I", arrival_a_jd, role="Sample A arrival (1I/'Oumuamua)")
    dist_a_au = oumu_a.distance_km / AU_TO_KM
    print(f"  JD returned: {oumu_a.epoch_tdb_jd}  ISO: {oumu_a.epoch_iso}")
    print(f"  r = {dist_a_au:.4f} AU  speed = {oumu_a.speed_km_s:.4f} km/s")
    print(f"  Expected ~5.8 AU  diff = {dist_a_au - 5.8:.4f} AU")

    print("Fetching oumuamua_sample_b_arrival (1I at Sample B arrival)...")
    oumu_b = fetch_state_vector("1I", arrival_b_jd, role="Sample B arrival (1I/'Oumuamua)")
    dist_b_au = oumu_b.distance_km / AU_TO_KM
    print(f"  JD returned: {oumu_b.epoch_tdb_jd}  ISO: {oumu_b.epoch_iso}")
    print(f"  r = {dist_b_au:.4f} AU  speed = {oumu_b.speed_km_s:.4f} km/s")
    print(f"  Expected ~111.4 AU  diff = {dist_b_au - 111.4:.4f} AU")

    # Load existing state_vectors.json, keep oumuamua_perihelion, replace all others
    print(f"\nLoading existing {DATA_PATH}...")
    existing = {}
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH) as f:
            raw = json.load(f)
        # Keep only oumuamua_perihelion (raw dict form)
        if "oumuamua_perihelion" in raw:
            existing["oumuamua_perihelion_raw"] = raw["oumuamua_perihelion"]
            print("  Kept oumuamua_perihelion")
        else:
            print("  WARNING: oumuamua_perihelion not found in existing JSON")

    # Write back: we merge below in fetch_c3_grid_new.py after the grid fetch.
    # Here we write a staging file with just the three pinned states.
    staging_path = os.path.join(os.path.dirname(__file__), "_pinned_staging.json")

    from solver.fetch import StateVector
    from dataclasses import asdict

    staging = {
        "earth_sample_ab_launch": {
            "type": "single",
            "body": earth_launch.body,
            "role": earth_launch.role,
            "epoch_tdb_jd": earth_launch.epoch_tdb_jd,
            "epoch_iso": earth_launch.epoch_iso,
            "frame": earth_launch.frame,
            "center": earth_launch.center,
            "retrieved_utc": earth_launch.retrieved_utc,
            "horizons_id": earth_launch.horizons_id,
            "position_km": earth_launch.position_km,
            "velocity_km_s": earth_launch.velocity_km_s,
        },
        "oumuamua_sample_a_arrival": {
            "type": "single",
            "body": oumu_a.body,
            "role": oumu_a.role,
            "epoch_tdb_jd": oumu_a.epoch_tdb_jd,
            "epoch_iso": oumu_a.epoch_iso,
            "frame": oumu_a.frame,
            "center": oumu_a.center,
            "retrieved_utc": oumu_a.retrieved_utc,
            "horizons_id": oumu_a.horizons_id,
            "position_km": oumu_a.position_km,
            "velocity_km_s": oumu_a.velocity_km_s,
        },
        "oumuamua_sample_b_arrival": {
            "type": "single",
            "body": oumu_b.body,
            "role": oumu_b.role,
            "epoch_tdb_jd": oumu_b.epoch_tdb_jd,
            "epoch_iso": oumu_b.epoch_iso,
            "frame": oumu_b.frame,
            "center": oumu_b.center,
            "retrieved_utc": oumu_b.retrieved_utc,
            "horizons_id": oumu_b.horizons_id,
            "position_km": oumu_b.position_km,
            "velocity_km_s": oumu_b.velocity_km_s,
        },
        "_tof_check": {
            "tof_a_days": tof_a_days,
            "tof_b_days": tof_b_days,
            "dist_a_au": dist_a_au,
            "dist_b_au": dist_b_au,
        }
    }

    with open(staging_path, "w") as f:
        json.dump(staging, f, indent=2)
    print(f"\nPinned states written to {staging_path}")
    print("Run fetch_c3_grid_new.py next to fetch grid windows and merge.")

if __name__ == "__main__":
    main()
