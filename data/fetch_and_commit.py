"""
fetch_and_commit.py — fetch all state vectors required by Phase 1 validation
and commit them to data/state_vectors.json.

Run once with live Horizons access. All subsequent validation runs are offline.
Per PROVENANCE.md ordering: Lyra source read would pin windows precisely;
since the source is not locally available, windows use the description bounds
("2017 launch, ~1 year / ~20 year flight") and are marked accordingly in
PROVENANCE.md GAP notes.

Window choices:
  Perihelion:   2017-Sep-09 TDB (JD 2458005.5) — single state
  C3 slice 2027: 2026-Jan-01 to 2028-Dec-31 daily — captures global minimum
  Sample A launch: 2017-Oct-19 to 2018-Jun-30 daily (post-discovery window)
    'Oumuamua discovered 2017-Oct-19; "2017 launch" must be after discovery.
  Sample A arrival: A-launch + 365 days (Lyra ~1 year flight)
  Sample B launch: same as A launch window
  Sample B arrival: B-launch + 7300 days (Lyra ~20 year flight, ~365.25 * 20)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astropy.time import Time
from solver.fetch import (
    OUMUAMUA_ID, fetch_state_vector, fetch_window, frame_check, save_state_vectors
)
from solver.constants import AU_TO_KM

# ---------------------------------------------------------------------------
# Epoch definitions (all TDB Julian Dates)
# ---------------------------------------------------------------------------

# 'Oumuamua perihelion: 2017-Sep-09 00:00 TDB
PERIHELION_JD = Time("2017-09-09", scale="tdb").jd
print(f"Perihelion epoch: {Time(PERIHELION_JD, format='jd', scale='tdb').iso}  JD={PERIHELION_JD:.4f}")

# Sample A/B launch window: 2017-Oct-19 (discovery date) to 2018-Jun-30
# "2017 launch" constrained to be after 2017-Oct-19 (discovery).
# Upper bound 2018-Jun-30 gives ~8 months of plausible early-window launches.
A_LAUNCH_START_JD = Time("2017-10-19", scale="tdb").jd
A_LAUNCH_STOP_JD  = Time("2018-06-30", scale="tdb").jd

# Sample A flight duration: ~365 days (Lyra "~1 year flight")
A_TOF_DAYS = 365
A_ARRIVAL_START_JD = A_LAUNCH_START_JD + A_TOF_DAYS
A_ARRIVAL_STOP_JD  = A_LAUNCH_STOP_JD  + A_TOF_DAYS

# Sample B flight duration: ~7305 days (Lyra "~20 year flight", 365.25 * 20)
B_TOF_DAYS = 7305
B_LAUNCH_START_JD = A_LAUNCH_START_JD   # same launch window
B_LAUNCH_STOP_JD  = A_LAUNCH_STOP_JD
B_ARRIVAL_START_JD = B_LAUNCH_START_JD + B_TOF_DAYS
B_ARRIVAL_STOP_JD  = B_LAUNCH_STOP_JD  + B_TOF_DAYS

# C3 slice window: 2026-Jan-01 to 2028-Dec-31 (captures 2027 optimal window)
C3_START_JD = Time("2026-01-01", scale="tdb").jd
C3_STOP_JD  = Time("2028-12-31", scale="tdb").jd

print(f"Sample A launch window: {Time(A_LAUNCH_START_JD, format='jd', scale='tdb').iso} "
      f"to {Time(A_LAUNCH_STOP_JD, format='jd', scale='tdb').iso} "
      f"({int(A_LAUNCH_STOP_JD - A_LAUNCH_START_JD)} days)")
print(f"Sample A arrival window: {Time(A_ARRIVAL_START_JD, format='jd', scale='tdb').iso} "
      f"to {Time(A_ARRIVAL_STOP_JD, format='jd', scale='tdb').iso}")
print(f"Sample B flight: ~{B_TOF_DAYS} days")
print(f"Sample B arrival window: {Time(B_ARRIVAL_START_JD, format='jd', scale='tdb').iso} "
      f"to {Time(B_ARRIVAL_STOP_JD, format='jd', scale='tdb').iso}")
print(f"C3 slice window: {Time(C3_START_JD, format='jd', scale='tdb').iso} "
      f"to {Time(C3_STOP_JD, format='jd', scale='tdb').iso} "
      f"({int(C3_STOP_JD - C3_START_JD)} days)")

# ---------------------------------------------------------------------------
# Fetch 1: 'Oumuamua at perihelion (single state, frame check)
# ---------------------------------------------------------------------------
print("\n--- Fetching 'Oumuamua at perihelion ---")
sv_perihelion = fetch_state_vector(OUMUAMUA_ID, PERIHELION_JD, role="self-check (perihelion)")
print(f"  Position (km): {[round(x, 1) for x in sv_perihelion.position_km]}")
print(f"  Velocity (km/s): {[round(v, 6) for v in sv_perihelion.velocity_km_s]}")
print(f"  Heliocentric distance: {sv_perihelion.distance_km / AU_TO_KM:.4f} AU")
print(f"  Heliocentric speed: {sv_perihelion.speed_km_s:.4f} km/s")
print(f"  v_inf (helio): {sv_perihelion.v_inf_helio():.4f} km/s  (target: 26.33 km/s)")

# Frame check: published perihelion speed ~87.7 km/s, inclination ~122 deg
fc = frame_check(sv_perihelion,
                 expected_speed_km_s=87.7, expected_incl_deg=122.0,
                 speed_tol=2.0, incl_tol=5.0)
print(f"  FRAME CHECK:")
print(f"    Speed: {fc['heliocentric_speed_km_s']:.4f} km/s "
      f"(expected ~{fc['expected_speed_km_s']}, diff={fc['speed_diff_km_s']:+.4f}) "
      f"{'OK' if fc['speed_ok'] else 'FAIL'}")
print(f"    Incl:  {fc['inclination_deg']:.3f} deg "
      f"(expected ~{fc['expected_incl_deg']}, diff={fc['incl_diff_deg']:+.3f}) "
      f"{'OK' if fc['incl_ok'] else 'FAIL'}")
print(f"    FRAME CONFIRMED: {fc['frame_confirmed']}")

if not fc["frame_confirmed"]:
    print("ERROR: frame check failed. Aborting — do not commit wrong-frame vectors.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Fetch 2: Earth over C3 slice window (daily)
# ---------------------------------------------------------------------------
print(f"\n--- Fetching Earth C3 slice window ({int(C3_STOP_JD - C3_START_JD + 1)} states) ---")
earth_c3 = fetch_window("399", C3_START_JD, C3_STOP_JD, role="C3 slice launch window (2027)")
print(f"  Fetched {len(earth_c3)} Earth states.")

# ---------------------------------------------------------------------------
# Fetch 3: Earth over sample A launch window
# ---------------------------------------------------------------------------
n_a = int(A_LAUNCH_STOP_JD - A_LAUNCH_START_JD + 1)
print(f"\n--- Fetching Earth sample A launch window ({n_a} states) ---")
earth_a_launch = fetch_window("399", A_LAUNCH_START_JD, A_LAUNCH_STOP_JD,
                               role="Sample A launch window")
print(f"  Fetched {len(earth_a_launch)} Earth states.")

# ---------------------------------------------------------------------------
# Fetch 4: 'Oumuamua over sample A arrival window
# ---------------------------------------------------------------------------
print(f"\n--- Fetching 'Oumuamua sample A arrival window ({n_a} states) ---")
oumuamua_a_arrival = fetch_window(OUMUAMUA_ID, A_ARRIVAL_START_JD, A_ARRIVAL_STOP_JD,
                                  role="Sample A arrival window")
print(f"  Fetched {len(oumuamua_a_arrival)} 'Oumuamua states.")

# ---------------------------------------------------------------------------
# Fetch 5: Earth over sample B launch window (same as A)
# ---------------------------------------------------------------------------
print(f"\n--- Fetching Earth sample B launch window ({n_a} states) ---")
earth_b_launch = fetch_window("399", B_LAUNCH_START_JD, B_LAUNCH_STOP_JD,
                               role="Sample B launch window")
print(f"  Fetched {len(earth_b_launch)} Earth states.")

# ---------------------------------------------------------------------------
# Fetch 6: 'Oumuamua over sample B arrival window
# ---------------------------------------------------------------------------
print(f"\n--- Fetching 'Oumuamua sample B arrival window ({n_a} states) ---")
oumuamua_b_arrival = fetch_window(OUMUAMUA_ID, B_ARRIVAL_START_JD, B_ARRIVAL_STOP_JD,
                                  role="Sample B arrival window")
print(f"  Fetched {len(oumuamua_b_arrival)} 'Oumuamua states.")

# ---------------------------------------------------------------------------
# Save all to data/state_vectors.json
# ---------------------------------------------------------------------------
entries = {
    "oumuamua_perihelion":     sv_perihelion,
    "earth_c3_2027":           earth_c3,
    "earth_sample_a_launch":   earth_a_launch,
    "oumuamua_sample_a_arrival": oumuamua_a_arrival,
    "earth_sample_b_launch":   earth_b_launch,
    "oumuamua_sample_b_arrival": oumuamua_b_arrival,
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_vectors.json")
save_state_vectors(out_path, entries)
print(f"\n--- Saved state_vectors.json: {out_path} ---")

# Summary
print("\n=== FETCH SUMMARY ===")
print(f"  1. 'Oumuamua perihelion (single): 1 state at JD {PERIHELION_JD:.2f}")
print(f"  2. Earth C3 2027 (window):        {len(earth_c3)} daily states")
print(f"  3. Earth sample A launch (window): {len(earth_a_launch)} daily states")
print(f"  4. 'Oumuamua sample A arrival (window): {len(oumuamua_a_arrival)} daily states")
print(f"  5. Earth sample B launch (window): {len(earth_b_launch)} daily states")
print(f"  6. 'Oumuamua sample B arrival (window): {len(oumuamua_b_arrival)} daily states")
print(f"  Frame check: {'CONFIRMED' if fc['frame_confirmed'] else 'FAILED'}")
print(f"  v_inf helio at perihelion: {sv_perihelion.v_inf_helio():.4f} km/s (target 26.33 km/s)")
