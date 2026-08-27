"""
fetch_c3_grid.py — fetch 'Oumuamua states for the 2027 C3 porkchop slice.

For each (departure, TOF) pair in the C3 grid, we need 'Oumuamua's position
at departure_epoch + TOF. With 1096 departures and TOF sweeping 300-4000 days
in 50-day steps (73 TOF values), we need 'Oumuamua over a wide arrival window.

Practical approach: fetch 'Oumuamua over the full arrival range.
  - Earliest departure: 2026-Jan-01, shortest TOF: 300 days -> 2026-Oct-28
  - Latest departure: 2028-Dec-31, longest TOF: 4000 days -> 2037-Dec-21

So 'Oumuamua arrival window: 2026-Oct-28 to 2037-Dec-31.
That is ~4081 days. At daily resolution this is a large fetch.

Use a coarser step (5 days) to keep the fetch tractable.
The validation grid also uses 5-day steps for the departure dimension.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from astropy.time import Time
from solver.fetch import OUMUAMUA_ID, fetch_window, load_state_vectors, save_state_vectors

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_vectors.json")

# Load existing entries
existing = load_state_vectors(DATA_PATH)

# 'Oumuamua arrival window for C3 grid
# Departure: 2026-Jan-01 (JD 2461041.5) to 2028-Dec-31 (JD 2462136.5), step 5d
# TOF: 300 to 4000 days, step 50d
# So arrival range: 2026-Jan-01+300 = 2026-Oct-28 to 2028-Dec-31+4000 = ~2039

arrival_start = Time("2026-10-28", scale="tdb").jd
arrival_stop  = Time("2038-12-31", scale="tdb").jd

print(f"Fetching 'Oumuamua C3 grid arrival window:")
print(f"  {Time(arrival_start, format='jd', scale='tdb').iso} to "
      f"{Time(arrival_stop, format='jd', scale='tdb').iso}")
n_days = int(arrival_stop - arrival_start)
step = 5
n_states = n_days // step + 1
print(f"  ~{n_states} states at {step}-day step")

oumu_c3_arrival = fetch_window(
    OUMUAMUA_ID,
    arrival_start, arrival_stop,
    role="C3 grid arrival window (2027 porkchop)",
    step_days=step,
)
print(f"  Fetched {len(oumu_c3_arrival)} states.")

# Also fetch Earth at 5-day steps over the departure window
earth_start = Time("2026-01-01", scale="tdb").jd
earth_stop  = Time("2028-12-31", scale="tdb").jd
print(f"\nFetching Earth C3 grid departure window (5-day step):")
earth_c3_grid = fetch_window(
    "399",
    earth_start, earth_stop,
    role="C3 grid departure window (2027 porkchop, 5d step)",
    step_days=step,
)
print(f"  Fetched {len(earth_c3_grid)} Earth states.")

# Save back with new keys
entries_new = {
    "oumuamua_c3_grid_arrival": oumu_c3_arrival,
    "earth_c3_grid_5d":         earth_c3_grid,
}

# Merge into existing and re-save
with open(DATA_PATH) as f:
    raw = json.load(f)

# Serialize new window entries
from solver.fetch import save_state_vectors as _save
_save.__module__  # ensure it's imported

# Use the save function for new entries, then merge
import tempfile, shutil
tmp_path = DATA_PATH + ".tmp"
_save(tmp_path, entries_new)

with open(tmp_path) as f:
    new_raw = json.load(f)

raw.update(new_raw)
with open(DATA_PATH, "w") as f:
    import json as _json
    _json.dump(raw, f, indent=2)

os.remove(tmp_path)

print(f"\nUpdated {DATA_PATH}")
print(f"Keys now in state_vectors.json: {list(raw.keys())}")
