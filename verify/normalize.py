"""
verify/normalize.py — lexical canonicalization of a candidate before matching.

## What this is, and what it is emphatically not

This is string rewriting. It maps typographic spellings of a character onto the
plain-ASCII character the manifest emits, and nothing else. It does not compare
magnitudes, does not round, does not parse a numeral into a value, and cannot
turn one number into another. `canonicalize("393.34")` is `"393.34"`; there is
no path through this module that makes it `"393.3"`.

That distinction is the whole reason the module exists as a separate layer. The
gate's guarantee is exact-string membership against renderings the solver
enumerated in advance, and every relaxation of a *match* erodes it. Nothing here
relaxes a match. It normalizes the candidate's typography so that a model
writing a real rendering in a real typeface is compared against the rendering it
actually wrote, rather than being rejected for the shape of a hyphen.

## Why it was needed

Granite, asked for prose a non-scientist can read, writes like a journal. It
produced `km² s⁻²` for `km^2/s^2` and, inside dates, U+2011 NON-BREAKING HYPHEN
for the ASCII hyphen in `2018-06-07`. The second is the worse of the two: the
ISO date pattern stops matching, the date fragments into a bare `06` and `07`
that the explanation never meant as quantities, and the gate reports two
fabricated numbers for a date that was written correctly.

Neither failure is about content. Both are about glyphs, and a gate that
rejects a correct number for its glyph is not being strict, it is being wrong.

## Why it is not in the matching path

verify/groundedness.py is walked by an AST test that fails the build on any
arithmetic or numeric conversion, because the gate must not be able to re-derive
a value it is supposed to be checking. This module is called by the gate but is
not the gate, and it holds no arithmetic either: `str.replace` and a translation
table. Keeping it separate means the matching path stays as small and as
readable as the guarantee it makes.

## The tables are closed

Both are enumerated. There is no general "strip anything unusual" rule, because
that is how a normalizer starts quietly repairing text into a match. A glyph
that is not in DASHES or SUPERSCRIPTS survives untouched and is rejected.
"""

from __future__ import annotations

import re

# Every Unicode dash and hyphen that stands in for the ASCII hyphen the manifest
# writes. U+2011 is the one seen live inside an ISO date; the rest are here
# because a model that reaches for one reaches for its neighbours.
DASHES = {
    "‐": "-",   # HYPHEN
    "‑": "-",   # NON-BREAKING HYPHEN
    "‒": "-",   # FIGURE DASH
    "–": "-",   # EN DASH
    "—": "-",   # EM DASH
    "―": "-",   # HORIZONTAL BAR
    "−": "-",   # MINUS SIGN
}

# Superscript glyphs to the plain character each stands for. The superscript
# minus matters as much as the digits, because "s⁻²" is "s^-2" and only then can
# the exponent rewrites below recognise it.
#
# Substituted a run at a time, not a character at a time. Per character, "⁻²"
# becomes "^-" then "^2", which is "^-^2" and matches nothing: the caret belongs
# to the exponent, not to each glyph in it.
SUPERSCRIPTS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3",
    "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
    "⁸": "8", "⁹": "9",
    "⁻": "-",  # SUPERSCRIPT MINUS
}

SUPERSCRIPT_RUN = re.compile("[" + "".join(SUPERSCRIPTS) + "]+")

# Multiplicative unit typography to the solidus form the manifest declares.
# Applied after the character maps, so the input here is already caret form.
# Ordered longest first: "km^2 s^-2" must be seen before "s^-2" alone could be.
#
# These are exact rewrites of complete unit strings, not a general algebra of
# exponents. "km^2 s^-2" and "km^2/s^2" are two spellings of one unit in the
# closed lexicon, and this table says so; it does not know what an exponent
# means and cannot combine one with another.
EXPONENT_FORMS = (
    ("km^2 s^-2", "km^2/s^2"),
    ("km^2 s^-1", "km^2/s"),
    ("km s^-2", "km/s^2"),
    ("km s^-1", "km/s"),
    ("km^2/s^2", "km^2/s^2"),
)

_DASH_MAP = str.maketrans(DASHES)


def _plain_exponents(text: str) -> str:
    """One caret per exponent run, then the run's plain characters."""
    return SUPERSCRIPT_RUN.sub(
        lambda m: "^" + "".join(SUPERSCRIPTS[ch] for ch in m.group()), text)


def canonicalize(text: str) -> str:
    """
    The candidate as the gate reads it.

    Idempotent: canonicalize(canonicalize(t)) == canonicalize(t), which matters
    because the gate's two checks each call it and neither knows whether the
    other ran first.

    Pure ASCII text containing none of the enumerated forms is returned
    unchanged, which is why the whole existing corpus is unaffected by this
    step.
    """
    out = _plain_exponents(text.translate(_DASH_MAP))
    for typographic, canonical in EXPONENT_FORMS:
        out = out.replace(typographic, canonical)
    return out
