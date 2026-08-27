"""
data/fetch_c3_grid_new.py — fetch C3 grid windows and merge into state_vectors.json.

Grid windows per PROVENANCE.md (revised):
  earth_c3_grid:    2018-01-01 to 2032-12-13, 14-day step (~392 states)
  oumuamua_c3_grid: 2023-01-01 to 2062-12-31, 14-day step (~1044 states)

After fetching, merges with:
  - oumuamua_perihelion  (from existing state_vectors.json)
  - pinned singles       (from _pinned_staging.json)

Produces the final state_vectors.json with exactly the six keys:
  oumuamua_perihelion, earth_sample_ab_launch,
  oumuamua_sample_a_arrival, oumuamua_sample_b_arrival,
  earth_c3_grid, oumuamua_c3_grid

Run from project root:
  python data/fetch_c3_grid_new.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astropy.time import Time
from solver.fetch import fetch_window
from solver.constants import AU_TO_KM

DATA_PATH    = os.path.join(os.path.dirname(__file__), "state_vectors.json")
STAGING_PATH = os.path.join(os.path.dirname(__file__), "_pinned_staging.json")

# Grid window bounds (calendar strings -> JDs at fetch time)
EARTH_GRID_START = "2018-01-01 00:00:00"
EARTH_GRID_STOP  = "2032-12-13 00:00:00"
OUMU_GRID_START  = "2023-01-01 00:00:00"
OUMU_GRID_STOP   = "2062-12-31 00:00:00"
STEP_DAYS = 14

def iso_to_jd(iso_str):
    return Time(iso_str, format="iso", scale="tdb").jd

def svs_to_json(svs, step_days):
    first = svs[0]; last = svs[-1]
    return {
        "type": "window",
        "body": first.body,
        "role": first.role,
        "window_start_tdb_jd": first.epoch_tdb_jd,
        "window_start_iso": first.epoch_iso,
        "window_end_tdb_jd": last.epoch_tdb_jd,
        "window_end_iso": last.epoch_iso,
        "step_days": step_days,
        "n_states": len(svs),
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
            for sv in svs
        ],
    }

def main():
    print("=== fetch_c3_grid_new.py ===")

    # Check staging file exists
    if not os.path.exists(STAGING_PATH):
        print(f"ERROR: {STAGING_PATH} not found. Run fetch_pinned.py first.")
        sys.exit(1)

    with open(STAGING_PATH) as f:
        staging = json.load(f)
    print(f"Loaded staging: {[k for k in staging if not k.startswith('_')]}")

    # Load existing state_vectors.json for oumuamua_perihelion
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: {DATA_PATH} not found.")
        sys.exit(1)
    with open(DATA_PATH) as f:
        existing_raw = json.load(f)
    if "oumuamua_perihelion" not in existing_raw:
        print("ERROR: oumuamua_perihelion not in existing state_vectors.json")
        sys.exit(1)
    perihelion_raw = existing_raw["oumuamua_perihelion"]
    print(f"  Kept oumuamua_perihelion epoch: {perihelion_raw['epoch_iso']}")

    # Fetch earth_c3_grid
    print(f"\nFetching earth_c3_grid (399, {EARTH_GRID_START} to {EARTH_GRID_STOP}, {STEP_DAYS}d step)...")
    start_jd = iso_to_jd(EARTH_GRID_START)
    stop_jd  = iso_to_jd(EARTH_GRID_STOP)
    earth_grid = fetch_window("399", start_jd, stop_jd,
                              role="C3 grid launch window (Earth)", step_days=STEP_DAYS)
    print(f"  Fetched {len(earth_grid)} states")
    print(f"  First: {earth_grid[0].epoch_iso}  Last: {earth_grid[-1].epoch_iso}")

    # Fetch oumuamua_c3_grid
    print(f"\nFetching oumuamua_c3_grid (1I, {OUMU_GRID_START} to {OUMU_GRID_STOP}, {STEP_DAYS}d step)...")
    oumu_start_jd = iso_to_jd(OUMU_GRID_START)
    oumu_stop_jd  = iso_to_jd(OUMU_GRID_STOP)
    oumu_grid = fetch_window("1I", oumu_start_jd, oumu_stop_jd,
                             role="C3 grid arrival window (1I/'Oumuamua)", step_days=STEP_DAYS)
    print(f"  Fetched {len(oumu_grid)} states")
    print(f"  First: {oumu_grid[0].epoch_iso}  Last: {oumu_grid[-1].epoch_iso}")
    dist_first_au = oumu_grid[0].distance_km / AU_TO_KM
    dist_last_au  = oumu_grid[-1].distance_km / AU_TO_KM
    print(f"  Distance range: {dist_first_au:.1f} AU to {dist_last_au:.1f} AU")

    # Merge into final output
    print(f"\nMerging into {DATA_PATH}...")
    out = {
        "oumuamua_perihelion": perihelion_raw,
        "earth_sample_ab_launch": staging["earth_sample_ab_launch"],
        "oumuamua_sample_a_arrival": staging["oumuamua_sample_a_arrival"],
        "oumuamua_sample_b_arrival": staging["oumuamua_sample_b_arrival"],
        "earth_c3_grid": svs_to_json(earth_grid, STEP_DAYS),
        "oumuamua_c3_grid": svs_to_json(oumu_grid, STEP_DAYS),
    }

    # Verify expected keys
    expected = {
        "oumuamua_perihelion", "earth_sample_ab_launch",
        "oumuamua_sample_a_arrival", "oumuamua_sample_b_arrival",
        "earth_c3_grid", "oumuamua_c3_grid",
    }
    assert set(out.keys()) == expected, f"Key mismatch: {set(out.keys())} vs {expected}"

    with open(DATA_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Written. Keys: {list(out.keys())}")

    # Verification checks
    print("\n=== Verification ===")
    tof_a = staging["_tof_check"]["tof_a_days"]
    tof_b = staging["_tof_check"]["tof_b_days"]
    dist_a = staging["_tof_check"]["dist_a_au"]
    dist_b = staging["_tof_check"]["dist_b_au"]

    launch_jd  = staging["earth_sample_ab_launch"]["epoch_tdb_jd"]
    arr_a_jd   = staging["oumuamua_sample_a_arrival"]["epoch_tdb_jd"]
    arr_b_jd   = staging["oumuamua_sample_b_arrival"]["epoch_tdb_jd"]

    print(f"ToF A: {arr_a_jd - launch_jd:.4f} days (expected ~{tof_a:.4f}, diff {abs(arr_a_jd - launch_jd - tof_a):.6f})")
    print(f"ToF B: {arr_b_jd - launch_jd:.4f} days (expected ~{tof_b:.4f}, diff {abs(arr_b_jd - launch_jd - tof_b):.6f})")
    print(f"Sample A distance: {dist_a:.4f} AU (expected ~5.8 AU)")
    print(f"Sample B distance: {dist_b:.4f} AU (expected ~111.4 AU)")
    print(f"earth_c3_grid:    {len(earth_grid)} states, {STEP_DAYS}d step")
    print(f"oumuamua_c3_grid: {len(oumu_grid)} states, {STEP_DAYS}d step")
    print("\nDone. staging file can be deleted.")

if __name__ == "__main__":
    main()
