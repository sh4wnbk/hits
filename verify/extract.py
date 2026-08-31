"""
verify/extract.py — telling a citable quantity from an incidental numeral.

The gate's hardest problem is not matching numbers. It is deciding which
numerals are claims about the world and which are labels. "714 km^2/s^2" must
be grounded; "eq. 4", "1I" and "2 samples" must not, or the gate rejects
correct prose and becomes something people route around.

Three clauses, evaluated in this order. The order is the defence.

  Clause 1, the override. A token adjacent to a unit, a HITS quantity noun, or
  a comparison marker is citable, and no exemption rescues it. This is first
  because a fabricated number's favourite disguise is a label: "eq. 4" is a
  reference, but "eq. 4 gives 4.2 km/s" grounds the 4.2, and a bare "4 km/s"
  is a measurement whatever precedes it.

  Clause 2, the closed table. A token is incidental only by matching one
  enumerated row in verify/exemptions.py, each anchored to a non-numeric marker
  and each justified by a corpus case. There is no row for calendar years.

  Clause 3, fail closed. Anything not exempted is citable. Anything the
  classifier cannot place is citable. A numeral written as words beside a unit
  or a quantity noun, or a numeral with two decimal points, is not a token that
  can be matched at all and is reported as such rather than skipped. Skipping
  it is how a number evades the gate by being unreadable.

The tokenizer is imported from verify.corpus_ingest, not reimplemented, so the
extraction rule and the manifest lookup cannot disagree about what a number is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from verify.corpus_ingest import all_tokens, sentence_at
from verify.exemptions import (
    COMPARISON_MARKERS, COUNTED_NOUNS, DOTTED_VERSION, EXEMPTION_ROWS,
    UNIT_LOOKAHEAD_CHARS,
    LIST_MARKER, MALFORMED_NUMERAL, OVERRIDE_WINDOW_WORDS, QUANTITY_NOUNS,
    REFERENCE_WORDS, SPELLED_RUN, UNIT_SPELLINGS, VERSION_ANCHORS,
)

CITABLE = "citable"
INCIDENTAL = "incidental"
REFERENCE = "reference"
SPELLED_OUT = "spelled-out"
MALFORMED = "malformed"


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    classification: str
    rule: str
    unit: Optional[str] = None
    frame: Optional[str] = None


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def _window(text: str, start: int, end: int) -> str:
    """
    Up to OVERRIDE_WINDOW_WORDS words either side, bounded by the sentence.

    Bounded because a unit in the next sentence says nothing about this token,
    and an unbounded window is how a check starts finding whatever it wants.
    """
    sentence, s_start = sentence_at(text, start)
    before = sentence[:start - s_start].split()
    after = sentence[end - s_start:].split()
    return " ".join(before[-OVERRIDE_WINDOW_WORDS:] + after[:OVERRIDE_WINDOW_WORDS])


def attached_unit(text: str, end: int) -> Optional[str]:
    """The unit immediately following a token, if any. Only what follows counts."""
    tail = text[end:end + UNIT_LOOKAHEAD_CHARS].lstrip()
    for spelling, canonical in UNIT_SPELLINGS:
        if tail.startswith(spelling):
            return canonical
    return None


UNIT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ^/²0123456789%")


def raw_unit_text(text: str, end: int) -> str:
    """
    The unit exactly as the explanation wrote it.

    The canonical form is what the manifest declares; this is what the reader
    sees. A finding has to name the written form, because "km/s^2" and "km/s"
    are different mistakes and reporting the canonical one would describe an
    error the author did not make.
    """
    tail = text[end:]
    stripped = tail.lstrip()
    run = ""
    for ch in stripped:
        if ch in UNIT_CHARS:
            run = run + ch
        else:
            break
    return run


def _preceding_word(text: str, start: int) -> str:
    words = text[:start].split()
    return words[-1].lower() if words else ""


def _following_word(text: str, end: int) -> str:
    words = text[end:].split()
    return words[0].lower().strip(".,;:") if words else ""


# ---------------------------------------------------------------------------
# The clauses
# ---------------------------------------------------------------------------

def _clause_1(text: str, tok: str, start: int, end: int) -> Optional[str]:
    """Citable by adjacency. Returns the reason, or None."""
    if attached_unit(text, end):
        return "clause1:unit"
    window = _window(text, start, end).lower()
    if any(noun in window for noun in QUANTITY_NOUNS):
        return "clause1:quantity-noun"
    if any(mk in window.split() or mk in window for mk in COMPARISON_MARKERS):
        return "clause1:comparison"
    return None


def _clause_2(text: str, tok: str, start: int, end: int) -> Optional[tuple]:
    """Incidental or reference by an enumerated row. Returns (row, routes_to)."""
    rows = {r.id: r for r in EXEMPTION_ROWS}

    # E1: a digit fused to an uppercase I. The tokenizer already refuses to
    # emit these, so reaching here means the fusion was not detected; the row
    # stays declared and tested so the rule is stated where it is read.
    if text[end:end + 1] == "I":
        return rows["E1"], rows["E1"].routes_to

    # E2: a reference word immediately before the numeral.
    if _preceding_word(text, start) in REFERENCE_WORDS:
        return rows["E2"], rows["E2"].routes_to

    # E4: a small count immediately before a counted noun.
    if tok.isdigit() and len(tok) <= 2 and int(tok) <= 10:
        if _following_word(text, end) in COUNTED_NOUNS:
            return rows["E4"], rows["E4"].routes_to

    # E5: a list marker.
    for m in LIST_MARKER.finditer(text):
        if m.start() <= start < m.end():
            return rows["E5"], rows["E5"].routes_to

    # E6: part of a dotted version named by a library.
    for m in DOTTED_VERSION.finditer(text):
        if m.start() <= start < m.end():
            if _preceding_word(text, m.start()) in VERSION_ANCHORS:
                return rows["E6"], rows["E6"].routes_to

    return None


def _ill_formed(text: str) -> List[Token]:
    """
    Constructs that are not well-formed numbers, found before classification
    because the clauses cannot classify what they cannot read.
    """
    out = []
    for m in MALFORMED_NUMERAL.finditer(text):
        if any(a.start() <= m.start() < a.end() and
               _preceding_word(text, a.start()) in VERSION_ANCHORS
               for a in DOTTED_VERSION.finditer(text)):
            continue   # a named version string, not a broken number
        out.append(Token(m.group(), m.start(), m.end(), MALFORMED,
                         "clause3:two-decimal-points"))

    for m in SPELLED_RUN.finditer(text):
        run = m.group()
        if run.lower() in ("one", "point"):
            continue   # ordinary English, not a numeral
        window = _window(text, m.start(), m.end()).lower()
        if attached_unit(text, m.end()) or any(n in window for n in QUANTITY_NOUNS):
            out.append(Token(run, m.start(), m.end(), SPELLED_OUT,
                             "clause3:spelled-out-beside-a-quantity"))
    return out


def extract(text: str) -> List[Token]:
    """Classify every numeral in an explanation."""
    tokens: List[Token] = _ill_formed(text)
    covered = [(t.start, t.end) for t in tokens]

    for tok, start, end in all_tokens(text):
        if any(a <= start < b for a, b in covered):
            continue

        reason = _clause_1(text, tok, start, end)
        if reason:
            tokens.append(Token(tok, start, end, CITABLE, reason,
                                unit=attached_unit(text, end)))
            continue

        hit = _clause_2(text, tok, start, end)
        if hit:
            row, routes_to = hit
            tokens.append(Token(tok, start, end, routes_to, row.id))
            continue

        tokens.append(Token(tok, start, end, CITABLE, "clause3:default",
                            unit=attached_unit(text, end)))

    return sorted(tokens, key=lambda t: t.start)


def citable(tokens: List[Token]) -> List[Token]:
    return [t for t in tokens if t.classification == CITABLE]
