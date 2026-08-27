"""
solver/constants.py — single definition of all physical constants used by HITS.

Per CONVENTIONS.md (Gravitational parameter): k is pinned once here and
imported everywhere. It is never redefined locally.
"""
from astropy.constants import GM_sun as _GM_sun_astropy
import astropy.units as u

# Sun's gravitational parameter in km^3/s^2.
# Source: astropy.constants.GM_sun (CODATA/IAU value).
# All solver modules and validation import this; none redefine it.
MU_SUN: float = _GM_sun_astropy.to("km3/s2").value  # ~1.32712440018e11 km^3/s^2

# Unit conversion factors applied at the fetch boundary (CONVENTIONS.md).
# 1 AU = 1.495978707e8 km (IAU 2012 definition, exact).
AU_TO_KM: float = 1.495978707e8
# 1 AU/day = AU_TO_KM / 86400 km/s
AU_DAY_TO_KM_S: float = AU_TO_KM / 86400.0
