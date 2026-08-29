"""
solver/lyra.py — the published Project Lyra constants HITS validates against.

Single source. These lived in conftest.py during Phase 1, which made them
reachable only from the test suite. The manifest emitter needs them too, and
CLAUDE.md requires the validation to be written once and imported by both the
test suite and the judges endpoints, so they move here and conftest imports
them.

Source (all five quantities, one paper):
  Hein, A. M., Perakis, N., Eubanks, T. M., Hibberd, A., Crowl, A., Hayward, K.,
  Kennedy, R. G. III, Osborne, R. (2019). "Project Lyra: Sending a spacecraft to
  1I/'Oumuamua (former A/2017 U1), the interstellar asteroid."
  Acta Astronautica 161, 552 to 561. DOI 10.1016/j.actaastro.2018.12.042.

Committed PDF: data/lyra/hein_2019_acta_161_552.pdf

Values here are the PAPER's, not HITS's. They are never re-rounded: a published
figure is quoted exactly as the source prints it (see docs/MANIFEST.md, the
rendering ladder policy for kind="published").
"""

from __future__ import annotations

# Bibliographic metadata. The publication year is carried as data rather than
# left as prose, so an explanation that says "the 2019 paper" has something to
# ground against.
PUBLICATION_YEAR: int = 2019
PUBLICATION_REFERENCE: str = (
    "Hein et al. 2019, Acta Astronautica 161, 552-561, "
    "DOI 10.1016/j.actaastro.2018.12.042"
)

LYRA_CONSTANTS = {
    "v_inf_helio_km_s": {
        "value": 26.33,
        "units": "km/s",
        "frame": "heliocentric",
        "tolerance_km_s": 0.5,
        "citation": "Hein et al. 2019, p.553 col 1 / abstract",
    },
    "c3_2027_km2_s2": {
        "value": 1400.0,
        "units": "km^2/s^2",
        "frame": "Earth-relative",
        "tolerance_frac": 0.20,
        "citation": "Hein et al. 2019, p.554 col 1 (37.4 km/s, ~15-yr duration)",
        # The paper states this same result as a departure velocity as well as
        # an energy. 37.4 km/s is the velocity form of the 1400 km^2/s^2 figure,
        # not a separate quantity, and PROVENANCE.md quotes it. It is emitted so
        # an explanation may state either form; without it, quoting the paper
        # accurately would be rejected.
        #
        # Earth-relative, like the C3 it restates. It sits inside the 33 to 76
        # km/s family recorded in EXCLUDED_NOT_TARGETS below, which is Earth-
        # departure and must never be labelled heliocentric.
        "published_departure_vinf_km_s": 37.4,
    },
    "c3_floor_km2_s2": {
        "value": 703.0,
        "units": "km^2/s^2",
        "frame": "Earth-relative",
        "tolerance_frac": 0.20,
        "citation": "Hein et al. 2019, p.553 col 2 / Fig.1",
    },
    "v_arr_sample_a_km_s": {
        "value": 13.6,
        "units": "km/s",
        "frame": "target-relative (asymptotic eq.4)",
        "tolerance_km_s": 2.0,
        "citation": "Hein et al. 2019, p.554 col 2 / Fig.5 (eq.4, launch 2017-06-07, ToF 1.0 yr, 5.8 AU)",
        "launch_epoch_tdb": "2017-06-07 12:00:00",
        "arrival_epoch_tdb": "2018-06-07 12:00:00",
        "tof_days": 365.0,
        # The paper states the flight time and the encounter distance. Both are
        # published figures in their own right, and both differ slightly from
        # what HITS computes: 365 days is 0.99932 Julian years, not 1.0, and the
        # 2026 orbit solution puts the encounter at 5.852 AU, not 5.8. The
        # manifest carries the published values separately so an explanation can
        # state the disagreement instead of eliding it.
        "published_tof_years": 1.0,
        "published_encounter_au": 5.8,
    },
    "v_arr_sample_b_km_s": {
        "value": 0.6,
        "units": "km/s",
        "frame": "target-relative (asymptotic eq.4)",
        "tolerance_km_s": 0.3,
        "citation": "Hein et al. 2019, p.554 col 2 / Fig.6 (eq.4, launch 2017-06-07, ToF 20.0 yr, 111.4 AU)",
        "launch_epoch_tdb": "2017-06-07 12:00:00",
        "arrival_epoch_tdb": "2037-06-07 12:00:00",
        "tof_days": 7305.0,
        "published_tof_years": 20.0,
        "published_encounter_au": 111.4,
    },
}

# Figures recorded so they are never mistaken for validation targets.
# See PROVENANCE.md, "Explicitly excluded, not comparison targets".
EXCLUDED_NOT_TARGETS = {
    "jga_solar_oberth_total_dv_m_s": {
        "value": 18332,
        "units": "m/s",
        "citation": "Hein et al. 2019, Table 1, p.557",
        "reason": "Total mission delta-v with a Jupiter flyby and a Solar Oberth "
                  "maneuver. Not reproducible by a patched-conic Lambert solve.",
    },
    "earth_departure_vinf_range_km_s": {
        "value": [33, 76],
        "units": "km/s",
        "citation": "Hein et al. 2019, p.554, restated p.555",
        "reason": "Earth-departure hyperbolic excess velocity for 30-to-5-year "
                  "durations at 2022-to-2027 launches. Same Earth-relative family "
                  "as the 1400 km^2/s^2 figure. Not a separate heliocentric quantity "
                  "and must not be labeled heliocentric.",
    },
}
