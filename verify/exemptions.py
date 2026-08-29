"""
verify/exemptions.py — the extraction rule's lexicons and exemption table, as data.

Everything the classifier decides with lives here, in tables, so a change is a
reviewable diff of the rule rather than an edit buried in control flow. Each
exemption row names the corpus case that justifies it; a row without one is a
rule nobody has tested.

The ordering these tables serve is in verify/extract.py and matters more than
any single entry: unit-bearing tokens are citable FIRST, and no exemption
rescues them. A fabricated number's favourite disguise is a label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

# ---------------------------------------------------------------------------
# Clause 1: the override lexicons
# ---------------------------------------------------------------------------

# Canonical unit to the spellings an explanation may write. The canonical form
# is the manifest's; the synonyms are what prose actually uses.
UNIT_SYNONYMS = {
    "km^2/s^2": ("km^2/s^2", "km2/s2", "km²/s²"),
    "km/s": ("km/s", "kilometres per second", "kilometers per second"),
    "km": ("km", "kilometres", "kilometers"),
    "AU": ("AU", "au", "astronomical units"),
    "d": ("days", "day"),
    "yr": ("years", "year", "yr"),
    "JD": ("JD", "Julian Date", "julian date"),
    "%": ("%", "percent", "per cent"),
    "deg": ("deg", "degrees"),
}

# Longest first so km^2/s^2 is recognised before km/s can match inside it.
UNIT_SPELLINGS: Tuple[Tuple[str, str], ...] = tuple(
    sorted((((sp, canon) for canon, sps in UNIT_SYNONYMS.items() for sp in sps)),
           key=lambda pair: len(pair[0]), reverse=True))

# The quantities HITS reports. A numeral next to one of these is a measurement
# however it is dressed. "duration" is included because the manifest carries
# duration_min_years, duration_max_years and both flight times: it is a HITS
# quantity, not a stray noun.
QUANTITY_NOUNS = (
    "delta-v", "delta v", "c3", "v_inf", "vinf", "excess velocity",
    "arrival velocity", "relative velocity", "arrival relative velocity",
    "tolerance", "difference", "gap", "agreement", "energy", "speed",
    "distance", "duration", "flight time", "time of flight", "velocity",
)

COMPARISON_MARKERS = (
    "vs", "vs.", "versus", "compared to", "compared with", "against",
    "within", "above", "below", "higher than", "lower than",
)

# How far Clause 1 looks either side of a token, in whitespace-separated words.
OVERRIDE_WINDOW_WORDS = 3


# ---------------------------------------------------------------------------
# Clause 2: the exemption table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExemptionRow:
    id: str
    description: str
    anchor: str          # the non-numeric marker the row is anchored to
    corpus_case: str     # the case that justifies the row existing
    routes_to: str = "incidental"


# E3 is deliberately absent. Every four-digit year is citable, because the
# manifest carries epoch years as entries (docs/MANIFEST.md, "Years are entries,
# not exemptions"). "Arrives in 2050" against a real 2037 arrival has to fail,
# and it can only fail if years are grounded like any other quantity.
EXEMPTION_ROWS = (
    ExemptionRow(
        "E1", "Interstellar-object designation: a digit fused to an uppercase I",
        anchor="the letter is part of the token (1I, 2I, 1I/'Oumuamua)",
        corpus_case="cc-004"),
    ExemptionRow(
        "E2", "Structured reference to the source document",
        anchor="a reference word immediately before (eq., Fig., p., Table)",
        corpus_case="cc-003",
        # NOT incidental. A reference number is checked against the manifest's
        # citation strings instead of its renderings. Exempting it outright
        # would let "per equation 7 of Hein et al." pass beside a real value,
        # which is the fabricated-number-as-label attack the mandate names, and
        # which bob-012 and bob-035 both make.
        routes_to="reference"),
    ExemptionRow(
        "E4", "Small enumerative count",
        anchor="an integer 0-10 immediately followed by a counted noun",
        corpus_case="cc-005"),
    ExemptionRow(
        "E5", "List marker",
        anchor="a digit and a period opening a line, or a parenthesised digit",
        corpus_case="cc-006"),
    ExemptionRow(
        "E6", "Digits inside an identifier or a version string",
        anchor="fused to word characters, or a dotted version after a "
               "library name",
        corpus_case="cc-007"),
)

REFERENCE_WORDS = (
    "eq.", "eq", "equation", "fig.", "fig", "figure", "table", "p.", "pp.",
    "page", "col.", "column", "section", "sec.", "ref.", "footnote",
)

COUNTED_NOUNS = (
    "sample", "samples", "transfer", "transfers", "case", "cases",
    "test", "tests", "quantity", "quantities", "body", "bodies",
    "step", "steps", "revolution", "revolutions", "result", "results",
)

# A dotted version is a version only when something names the software.
VERSION_ANCHORS = (
    "hapsira", "astropy", "numpy", "scipy", "astroquery", "plotly", "pytest",
    "python", "version", "v",
)

LIST_MARKER = re.compile(r"(?:^|\n)\s*\d+\.\s|\(\d+\)")
DOTTED_VERSION = re.compile(r"\d+(?:\.\d+){2,}")


# ---------------------------------------------------------------------------
# Clause 3: constructs that are not well-formed numbers
# ---------------------------------------------------------------------------

# Written-out numerals. Detected only next to a unit or a quantity noun, where
# they are a measurement being kept out of digits.
SPELLED_NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "point",
)
SPELLED_RUN = re.compile(
    r"\b(?:" + "|".join(SPELLED_NUMBER_WORDS) + r")"
    r"(?:[\s-]+(?:" + "|".join(SPELLED_NUMBER_WORDS) + r"))*\b",
    re.IGNORECASE)

# More than one decimal point, which no reader can resolve and no manifest
# rendering can match.
MALFORMED_NUMERAL = re.compile(r"\d+\.\d+\.\d+")
