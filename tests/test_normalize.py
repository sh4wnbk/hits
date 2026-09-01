"""
tests/test_normalize.py — typography is canonicalized, magnitudes are not.

Two claims, and the second is the one that matters. The first is that the
typographic forms Granite actually produced now reach the gate as the forms the
manifest emits. The second is that nothing here can turn one number into
another, because the moment a normalizer can do that, the gate's exact-string
guarantee is gone and no test above it means anything.
"""

import pytest

from verify.normalize import (canonicalize, DASHES, SPACES, SUPERSCRIPTS,
                              EXPONENT_FORMS)


# ---------------------------------------------------------------------------
# What it fixes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("written,canonical", [
    # Seen live, verbatim, on 2026-08-30.
    ("393.34 km² s⁻²", "393.34 km^2/s^2"),
    ("19.8328 km s⁻¹", "19.8328 km/s"),
    ("2919.78 km²/s²", "2919.78 km^2/s^2"),
    # U+2011 NON-BREAKING HYPHEN inside an ISO date, which is what broke the
    # date into a bare 06 and 07 the explanation never wrote as quantities.
    ("2018‑06‑07", "2018-06-07"),
    # Seen live, verbatim, on 2026-08-31, in one borisov run that floored on
    # all three attempts. The middle dot tears the exponent off its unit: the
    # gate saw a wrong-unit on km^2 and a loose 2 beside it.
    ("1727.89 km\u00b7s\u207b\u00b9", "1727.89 km/s"),
    ("1727.89 km\u00b2\u00b7s\u207b\u00b2", "1727.89 km^2/s^2"),
    ("41.56787 km\u22c5s\u207b\u00b9", "41.56787 km/s"),
    # U+00A0 between the parts of a date, which stopped the phrase matching the
    # rendering it is and left a bare 13 reported as fabricated.
    ("March 13,\u00a02030", "March 13, 2030"),
    # Already canonical, untouched.
    ("393.34 km^2/s^2 on 2018-06-07", "393.34 km^2/s^2 on 2018-06-07"),
])
def test_typographic_forms_reach_the_gate_as_the_manifest_writes_them(
        written, canonical):
    assert canonicalize(written) == canonical


def test_an_exponent_run_takes_one_caret():
    """
    Per character, "⁻²" canonicalizes to "^-" then "^2", which is "^-^2" and
    matches nothing. The caret belongs to the exponent, not to each glyph in
    it. This is the bug the run-at-a-time substitution exists to prevent.
    """
    assert canonicalize("s⁻²") == "s^-2"
    assert "^-^" not in canonicalize("km² s⁻²")


def test_canonicalize_is_idempotent():
    """
    Both of the gate's checks call it and neither knows whether the other ran
    first, so running it twice has to be running it once.
    """
    for sample in ("393.34 km² s⁻²", "2018‑06‑07", "plain text 1.5",
                   "km s⁻¹", ""):
        once = canonicalize(sample)
        assert canonicalize(once) == once


# ---------------------------------------------------------------------------
# What it must never do
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    "393.34", "393.3", "393", "0.044", "26.286", "26.33", "1331.16",
    "2919.78", "7305", "20", "2030", "13.96737",
])
def test_no_numeral_is_ever_altered(value):
    """
    The guarantee. Canonicalization is typography; it is not tolerance, not
    rounding, and not a comparison of magnitudes. A normalizer that could turn
    393.34 into 393.3 would be doing the gate's rejecting for it.
    """
    assert canonicalize(value) == value
    assert canonicalize(f"the figure is {value} km/s") == f"the figure is {value} km/s"


def test_a_wrong_number_stays_wrong_however_it_is_typeset():
    """
    The failure this must not paper over: a fabricated value dressed in the
    same typography the real ones use is still a different string afterwards.
    """
    assert canonicalize("393.35 km² s⁻²") == "393.35 km^2/s^2"
    assert canonicalize("393.34 km² s⁻²") != canonicalize("393.35 km² s⁻²")


def test_an_unlisted_glyph_survives_and_is_not_quietly_repaired():
    """
    Both tables are closed on purpose. A general "strip anything unusual" rule
    is how a normalizer starts editing text into a match, so a glyph nobody
    enumerated passes through and is rejected downstream.
    """
    assert canonicalize("393٫34") == "393٫34"   # ARABIC DECIMAL SEPARATOR
    assert canonicalize("３９３") == "３９３"  # fullwidth digits


def test_the_tables_are_enumerated_not_generated():
    """Every entry is a literal a reviewer can read in a diff."""
    assert all(v == "-" for v in DASHES.values())
    assert all(v == " " for v in SPACES.values())
    assert set(SUPERSCRIPTS.values()) == set("0123456789-")
    assert all(canon.count("/") == 1 for _, canon in EXPONENT_FORMS)


def test_the_multiplication_sign_is_not_folded():
    """
    U+00D7 sits between numbers as often as between units, so folding it would
    move the boundary between two quantities rather than repair a glyph. It is
    absent from the table on purpose and the absence is asserted, because a
    later hand adding it would look like completeness.
    """
    assert "\u00d7" not in SPACES
    assert canonicalize("3 \u00d7 10") == "3 \u00d7 10"


def test_a_space_between_digits_is_not_closed_up():
    """
    The one repair deliberately not made. `1 727.89` is the SI thousands
    spelling of a real rendering and it stays rejected, because a rule that
    joins adjacent digit groups is a rule that can assemble a value the model
    never wrote. Asserted for the narrow spaces too: they are folded to an
    ASCII space and stop there.
    """
    assert canonicalize("1 727.89") == "1 727.89"
    assert canonicalize("1\u202f727.89") == "1 727.89"
    assert canonicalize("1\u00a0727.89") == "1 727.89"


def test_no_fabricated_value_enters_through_any_typography():
    """
    The property the whole widening rests on. Canonicalization changes glyphs,
    never digits, so a value the solver never emitted is the same wrong string
    afterwards in every spelling this module knows.
    """
    real, fake = "1727.89", "1727.99"
    forms = ["{v} km^2/s^2", "{v} km\u00b2\u00b7s\u207b\u00b2",
             "{v} km\u22c5s\u207b\u00b9", "{v}\u00a0km\u00b2/s\u00b2"]
    for form in forms:
        assert canonicalize(form.format(v=fake)) != canonicalize(
            form.format(v=real))
        assert fake in canonicalize(form.format(v=fake))
