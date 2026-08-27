"""Extend 'Oumuamua C3 arrival window to 2040 and re-save."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from astropy.time import Time
from solver.fetch import OUMUAMUA_ID, fetch_window, load_state_vectors

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_vectors.json")

# Fetch 2039 and 2040 extension
ext_start = Time("2039-01-01", scale="tdb").jd
ext_stop  = Time("2040-12-31", scale="tdb").jd

print(f"Fetching 'Oumuamua C3 arrival extension: 2039-2040 at 5-day step")
ext_states = fetch_window(OUMUAMUA_ID, ext_start, ext_stop,
                          role="C3 grid arrival window extension 2039-2040",
                          step_days=5)
print(f"  Fetched {len(ext_states)} states.")

# Load existing JSON and merge
with open(DATA_PATH) as f:
    raw = json.load(f)

# Append to existing oumuamua_c3_grid_arrival states
existing_states = raw["oumuamua_c3_grid_arrival"]["states"]
new_states = [
    {"epoch_tdb_jd": sv.epoch_tdb_jd, "epoch_iso": sv.epoch_iso,
     "position_km": sv.position_km, "velocity_km_s": sv.velocity_km_s}
    for sv in ext_states
]
raw["oumuamua_c3_grid_arrival"]["states"].extend(new_states)
raw["oumuamua_c3_grid_arrival"]["n_states"] = len(raw["oumuamua_c3_grid_arrival"]["states"])
raw["oumuamua_c3_grid_arrival"]["window_end_tdb_jd"] = ext_stop
raw["oumuamua_c3_grid_arrival"]["window_end_iso"] = Time(ext_stop, format='jd', scale='tdb').iso

with open(DATA_PATH, "w") as f:
    json.dump(raw, f, indent=2)

print(f"Updated state_vectors.json. Total 'Oumuamua C3 arrival states: "
      f"{raw['oumuamua_c3_grid_arrival']['n_states']}")
