"""
fetch_objects.py — fetch and commit the state vectors for the two interstellar
objects HITS computes but cannot validate: 2I/Borisov and 3I/ATLAS.

Run once with live Horizons access. Everything downstream is offline.

## Why these epochs

No published intercept study exists for either object, so there is no window to
reproduce and nothing to match. The transfer each object gets is chosen by a
stated rule rather than taken from a source, and the rule is the same for both:

  the cheapest departure day in calendar year 2030, for a flight of 7305 days.

2030 is after discovery for both objects and after the retrieval date, so the
departure is a departure and not a hindcast. 7305 days is 20 years to the day
on the 365.25-day year, which is the flight duration Hein et al. 2019 used for
Project Lyra's Sample B, so the two unvalidated transfers sit in the same
duration class as the one 'Oumuamua transfer that does have a published figure
behind it.

The day was found by solving every departure day in 2030 at that flight time
against the matching arrival state, and taking the minimum C3. Both minima are
interior to the year, not on its edge. That scan is exploratory and is not
committed; what is committed is the four states the chosen transfers read.

## Frame check

The 'Oumuamua frame check compares heliocentric speed and inclination against
published figures. Neither of these objects has a published intercept study,
and quoting orbital elements from recall would be exactly the fabricated
citation this repository refuses. So the check here is independent instead of
published: the ecliptic osculating elements derived from the fetched state
vector are compared against the elements Horizons itself reports for the same
body at the same epoch, requested separately. If the state came back in the
equatorial frame the two inclinations would differ by up to 23.4 degrees, and
if the center were the barycentre rather than the Sun the eccentricity would
move. Agreement to five decimals confirms both.
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
from astropy.time import Time
from astroquery.jplhorizons import Horizons

from solver.constants import AU_TO_KM, MU_SUN
from solver.fetch import fetch_state_vector, save_state_vectors

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_vectors.json")

TOF_DAYS = 7305.0  # 20 years on the 365.25-day year; the Lyra Sample B duration

# (state key, Horizons id, epoch, role)
TRANSFERS = [
    {
        "object": "2I/Borisov",
        "horizons_id": "2I",
        "departure_iso": "2030-03-13",
        "arrival_iso": "2050-03-13",
        "earth_key": "earth_borisov_departure",
        "target_key": "borisov_arrival",
    },
    {
        "object": "3I/ATLAS",
        "horizons_id": "3I",
        "departure_iso": "2030-09-20",
        "arrival_iso": "2050-09-20",
        "earth_key": "earth_atlas_departure",
        "target_key": "atlas_arrival",
    },
]


def elements_from_state(sv):
    """Ecliptic osculating e, inclination (deg) and perihelion distance (AU)."""
    r, v = sv.r, sv.v
    r_mag = float(np.linalg.norm(r))
    h = np.cross(r, v)
    h_mag = float(np.linalg.norm(h))
    e_vec = np.cross(v, h) / MU_SUN - r / r_mag
    e = float(np.linalg.norm(e_vec))
    incl = math.degrees(math.acos(np.clip(h[2] / h_mag, -1.0, 1.0)))
    a = 1.0 / (2.0 / r_mag - float(np.dot(v, v)) / MU_SUN)
    return e, incl, a * (1.0 - e) / AU_TO_KM


def horizons_elements(horizons_id, jd):
    """The elements Horizons reports for the same body at the same epoch."""
    el = Horizons(id=horizons_id, location="@sun", epochs=jd).elements(refplane="ecliptic")
    return float(el["e"][0]), float(el["incl"][0]), float(el["q"][0])


new_entries = {}
failed = False

for t in TRANSFERS:
    dep_jd = Time(t["departure_iso"], scale="tdb").jd
    arr_jd = Time(t["arrival_iso"], scale="tdb").jd
    assert abs((arr_jd - dep_jd) - TOF_DAYS) < 1e-6, (
        f"{t['object']}: arrival minus departure is {arr_jd - dep_jd}, not {TOF_DAYS}")

    print(f"\n=== {t['object']} ===")
    print(f"  departure {t['departure_iso']} (JD {dep_jd:.1f})  "
          f"arrival {t['arrival_iso']} (JD {arr_jd:.1f})  TOF {TOF_DAYS:.0f} d")

    earth_sv = fetch_state_vector(
        "399", dep_jd, role=f"{t['object']} intercept departure (Earth)")
    target_sv = fetch_state_vector(
        t["horizons_id"], arr_jd, role=f"{t['object']} intercept arrival")

    print(f"  Earth  r = {earth_sv.distance_km / AU_TO_KM:.4f} AU   "
          f"|v| = {earth_sv.speed_km_s:.4f} km/s")
    print(f"  Target r = {target_sv.distance_km / AU_TO_KM:.4f} AU   "
          f"|v| = {target_sv.speed_km_s:.4f} km/s   "
          f"v_inf helio = {target_sv.v_inf_helio():.4f} km/s")
    print(f"  outgoing leg: dot(r, v) = {float(np.dot(target_sv.r, target_sv.v)):.4e} "
          f"({'outgoing' if float(np.dot(target_sv.r, target_sv.v)) > 0 else 'INGOING'})")

    e_s, i_s, q_s = elements_from_state(target_sv)
    e_h, i_h, q_h = horizons_elements(t["horizons_id"], arr_jd)
    ok = (abs(e_s - e_h) < 1e-4 and abs(i_s - i_h) < 1e-3 and abs(q_s - q_h) < 1e-4)
    print(f"  FRAME CHECK (state-derived vs Horizons elements, same epoch)")
    print(f"    e     {e_s:.5f} vs {e_h:.5f}   diff {e_s - e_h:+.2e}")
    print(f"    incl  {i_s:.4f} vs {i_h:.4f} deg   diff {i_s - i_h:+.2e}")
    print(f"    q     {q_s:.5f} vs {q_h:.5f} AU   diff {q_s - q_h:+.2e}")
    print(f"    hyperbolic: e > 1 is {e_s > 1.0}")
    print(f"    FRAME CONFIRMED: {ok}")
    if not ok or e_s <= 1.0:
        print("  ERROR: check failed. Not committing this object.")
        failed = True
        continue

    new_entries[t["earth_key"]] = earth_sv
    new_entries[t["target_key"]] = target_sv

if failed:
    print("\nAborting: at least one object failed its frame check.")
    sys.exit(1)

# Merge into the committed file. The existing entries are read and written
# back unchanged; nothing in the 'Oumuamua validation set is recomputed here.
with open(DATA_PATH) as f:
    existing = json.load(f)

tmp = DATA_PATH + ".new"
save_state_vectors(tmp, new_entries)
with open(tmp) as f:
    added = json.load(f)
os.remove(tmp)

for key in added:
    if key in existing:
        print(f"\nERROR: {key} already committed. Refusing to overwrite.")
        sys.exit(1)

existing.update(added)
with open(DATA_PATH, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n=== committed {len(added)} new entries to {DATA_PATH} ===")
for key in added:
    print(f"  {key}: {added[key]['role']} @ {added[key]['epoch_iso']}")
