"""
verify/groundedness.py — the deterministic groundedness gate.

Two checks, and `Verdict.checks_run` records which ran.

The membership test is the dispositive one. Every citable token in an
explanation must appear in the manifest for the call that produced it, matched
as a string against the renderings the solver emitted in advance. The gate does
not round, does not convert, and does not compute: if it could re-derive 1.62%
from 714.36 and 703, what it would certify is that it can do arithmetic, not
that the explanation is grounded. tests/test_groundedness.py walks this file's
AST and reds the build if a numeric conversion, rounding, absolute value, or
arithmetic operator ever appears here.

Unit and frame are dispositive too, and for the same reason they are separate
fields in the solver: 714.36 km^2/s^2 and 714.36 km/s are different claims, and
an Earth-relative C3 called heliocentric is a different quantity that happens
to share a number. Matching digits is not enough.

The attribution check: published versus computed.

Bob's corpus produced nine cases where a real number is attached to the wrong
result. Evaluating the specified membership rule against them showed it accepts
all nine, because the token is in the manifest with a matching unit and frame
and the wrongness is in what the number is claimed to be. Seven of those nine
are decidable without knowing anything about results: they turn on whether a
value the manifest marks `published` is being passed off as the system's own,
or the reverse. That is a lookup on `entry.kind` and a phrase list.

PROVENANCE.md is built around exactly this distinction, and CLAUDE.md requires
that offline and credentialed, computed and published figures never be
mis-credited to each other. This is that requirement made mechanical.

What this check must never become: it does no arithmetic, and it decides
nothing by recomputing a value. It compares strings against manifest metadata.
tests/test_groundedness.py::test_gate_does_no_arithmetic walks this file's AST
and reds the build if a numeric conversion, rounding, absolute value, or
arithmetic operator appears.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# The tokenizer and sentence scope are imported, not reimplemented, so the gate
# and the ingest triage cannot disagree about what counts as a quoted number.
from verify.corpus_ingest import (
    tokens_in_manifest, sentence_before, sentence_after,
    nearest_position, find_in_sentence,
)
from verify.normalize import canonicalize
from verify.extract import (
    extract, raw_unit_text, CITABLE, REFERENCE, SPELLED_OUT, MALFORMED,
)
from verify.exemptions import REFERENCE_WORDS

# ---------------------------------------------------------------------------
# The lexicon, held as data
# ---------------------------------------------------------------------------

COMPUTED_SIDE = (
    "hits computes", "hits gives", "hits places", "hits finds", "hits solves",
    "the solver", "solver's", "computed", "we compute", "we place",
    "calculated", "our result",
)

PUBLISHED_SIDE = (
    "published", "the paper", "the source", "hein", "lyra", "et al",
    "reported", "reports", "fig.", "figure", "p.55", "table",
)

# A comparison introduces its target. "against 703 km^2/s^2" names the
# published value without a provenance word anywhere, and that is ordinary
# correct prose: the whole point of the validation is reporting a computed
# figure against a published one. Kept separate from PUBLISHED_SIDE because
# these are not provenance words; they are what marks the other side of a
# comparison. None of the seam cases introduces its published token this way,
# which is what makes the distinction safe.
COMPARATIVE_INTRODUCERS = (
    "against", "versus", " vs ", " vs. ", "compared to", "compared with",
    "relative to the published", "as opposed to",
)

# How far past a token a trailing published marker still introduces it.
# "against 26.33 km/s published" is a correct attribution with the marker
# behind the value and its unit, and it appears in the accept corpus, so the
# check has to see it. Kept short on purpose: a marker further along the
# sentence belongs to a different clause.
TRAILING_MARKER_CHARS = 24

# Attribution is a verb, not proximity. "which HITS labels as a published
# benchmark value" asserts a kind; "1.6% above Lyra's figure" compares against
# one. Without this distinction the check flags correct comparative prose, and
# the accept corpus is full of correct comparative prose.
LABELLED_PUBLISHED = re.compile(
    r"\b(labels?|labell?ed|described?|calls?|called|presented?|reports?|"
    r"reported|treats?|treated)\b[^.;:]{0,40}?\bas\b\s+"
    r"(?:an?\s+|the\s+)?(?:published|benchmark)",
    re.IGNORECASE,
)


# Attribution to a source, as opposed to labelling a value published. The two
# are different sentences: "labelled as a published benchmark" asserts a kind,
# and "reported in the source paper" asserts an origin. Only the first was ever
# checked, so a computed figure credited to a paper passed the gate.
#
# This fires only against a manifest that declares no published entry at all,
# which is why it can be this broad without touching correct comparative prose.
# Where a published entry exists, comparing a computed value against it and
# naming the paper is exactly what the answer is supposed to do.
#
# The deterministic floor is the constraint that shaped the pattern. It says
# "the quantity the mission-design literature compares against", which names
# the literature without attributing a figure to it, and a pattern that flagged
# it would make the floor fail its own gate and leave nothing safe to serve.
# The verb and the preposition are what separate the two, and they are required.
SOURCE_ATTRIBUTION = re.compile(
    r"\b(?:reported|published|quoted|cited|given|found|stated|noted|appears?|"
    r"appearing|taken|drawn|described)\b[^.;:]{0,30}?\b(?:in|by|from)\b\s+"
    r"(?:the\s+|a\s+|an\s+|this\s+|its\s+|their\s+)?"
    r"(?:source\s+|published\s+|original\s+|reference\s+|prior\s+)?"
    r"(?:paper|papers|study|studies|literature|reference|references|source|"
    r"sources|publication|publications|article|articles)\b"
    r"|\baccording to\b[^.;:]{0,40}?\b(?:paper|study|literature|source|"
    r"publication|article)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    text: str
    reason: str
    start: int
    note: str = ""


def _introduced_published(text: str, pos: int, token: str) -> bool:
    """
    Whether anything in the sentence presents this token as a published figure.

    Before the token, or immediately behind it and its unit. Both forms occur
    in correct prose: "against the published 26.33 km/s" and "against 26.33
    km/s published".
    """
    before = sentence_before(text, pos).lower()
    if any(mk in before for mk in PUBLISHED_SIDE):
        return True
    if any(mk in before for mk in COMPARATIVE_INTRODUCERS):
        return True
    tail = sentence_after(text, pos)[len(token):len(token) + TRAILING_MARKER_CHARS].lower()
    return any(mk in tail for mk in PUBLISHED_SIDE)


def check_attribution(text: str, manifest) -> List[Finding]:
    """
    Every token whose claimed provenance contradicts the manifest's.

    Two directions, and they are not symmetric, because the prose is not.

    A published value stated without anything presenting it as published is
    being offered as the system's own result. Absence is the signal: HITS never
    computed Lyra's 703, so a sentence that states it as a finding is wrong
    however it is phrased.

    A computed value is only mis-stated when the sentence actively labels it
    published. Absence proves nothing there, because most correct sentences
    about a computed number say nothing about provenance at all.
    """
    text = canonicalize(text)
    findings: List[Finding] = []
    index = manifest.index()

    for token, pos, entries in tokens_in_manifest(text, index):
        kinds = {e.kind for e in entries}

        if kinds == {"published"}:
            if not _introduced_published(text, pos, token):
                findings.append(Finding(
                    text=token, reason="attribution-mismatch", start=pos,
                    note=f"{token} is published only "
                         f"({sorted(e.id for e in entries)[0]}), stated as the "
                         "system's own result"))

        elif kinds and kinds <= {"computed", "derived"}:
            if LABELLED_PUBLISHED.search(sentence_after(text, pos)):
                findings.append(Finding(
                    text=token, reason="attribution-mismatch", start=pos,
                    note=f"{token} is computed "
                         f"({sorted(e.id for e in entries)[0]}), labelled as a "
                         "published figure"))

    findings.extend(_unsourced_attributions(text, manifest))
    return findings


def _unsourced_attributions(text: str, manifest) -> List[Finding]:
    """
    A source credited by a manifest that has no source.

    2I/Borisov and 3I/ATLAS have no published intercept study, and that absence
    is the whole content of their verification status. A Granite answer about
    Borisov nonetheless closed with "the asymptotic value of 16.93682 km/s
    reported in the source paper". Every number in it was grounded; the paper
    does not exist.

    The check above could not see it. It asks whether a token is labelled as
    published, and that sentence labels nothing: it states an origin. Widening
    that pattern to catch the phrasing was measured and would flag correct
    comparative prose, where a computed figure is set against a real published
    one in the same sentence.

    So the question asked here is not about the phrasing but about the
    manifest. Where the solver declared no published entry, no figure in the
    answer has a source to be reported in, and any sentence claiming one is
    false whatever its wording. Where a published entry does exist, this says
    nothing at all and the two clauses above do the work.

    The finding is on the phrase rather than on a number, because the fabricated
    thing is the attribution. There is no token to name: the figure was real.
    """
    if any(e.kind == "published" for e in manifest.entries):
        return []
    return [
        Finding(text=m.group(), reason="unsourced-attribution", start=m.start(),
                note="this manifest declares no published entry, so no figure "
                     "in it was reported in a source")
        for m in SOURCE_ATTRIBUTION.finditer(text)
    ]


# ---------------------------------------------------------------------------
# The gate entrypoint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    """
    The result of running the gate over one explanation.

    `checks_run` is not decoration. While the gate is partial, a caller reading
    only `grounded` would take a pass as a guarantee the gate cannot yet make,
    and that mistake is the exact failure this whole layer exists to prevent.

    `advisory` is the slot for Granite Guardian, which is a second opinion and
    never the verdict. CLAUDE.md is explicit that the deterministic comparison
    is dispositive and Guardian is advisory on top of it, so the field reports
    `unavailable` rather than being absent: an advisory layer that is silently
    missing looks the same as one that agreed.
    """
    findings: List[Finding]
    checks_run: tuple
    advisory: str = "unavailable"

    @property
    def grounded(self) -> bool:
        return not self.findings


# Words that name a frame, and the frame each names.
FRAME_WORDS = {
    "heliocentric": "heliocentric",
    "earth-relative": "earth_relative",
    "earth-departure": "earth_relative",
    "earth relative": "earth_relative",
    "target-relative": "target_relative",
    "target relative": "target_relative",
    "relative to the sun": "heliocentric",
}

# How far a frame word reaches. A frame word in the same sentence qualifies the
# quantity that sentence is about; one in the next sentence does not.
FRAME_SCOPE = "sentence"


def _citation_index(manifest) -> set:
    """
    The reference tokens the source citations actually contain.

    A reference number is grounded against this, not against the renderings.
    "Fig. 5" and "eq. 4" appear in the manifest's citation strings; "Fig. 3" and
    "equation 7" do not, and a fabricated reference beside a real value is the
    disguise the mandate names.
    """
    out = set()
    for entry in manifest.entries:
        if not entry.citation:
            continue
        for word in REFERENCE_WORDS:
            for piece in entry.citation.lower().split(word):
                stripped = piece.lstrip(". ")
                digits = ""
                for ch in stripped:
                    if ch.isdigit():
                        digits = digits + ch
                    else:
                        break
                if digits:
                    out.add(digits)
    return out


def _framed_positions(text: str, manifest) -> List[int]:
    """Positions of tokens that carry a real frame, in order."""
    index = manifest.index()
    out = []
    for token in extract(text):
        if token.classification != CITABLE:
            continue
        entries = index.get(token.text)
        if entries and "n_a" not in {e.frame for e in entries}:
            out.append(token.start)
    return out


def _frame_conflict(text: str, pos: int, entries, manifest) -> str:
    """
    The frame word that qualifies THIS token and contradicts it.

    A frame word attaches to the nearest quantity that has a frame at all, not
    to every number in its sentence. Scanning the whole sentence flags the
    wrong quantity as soon as a sentence names two frames, and correct prose
    does that constantly: "the C3 floor sits near 714 km^2/s^2 ... and the
    heliocentric check comes in at 26.3 km/s" describes both correctly, and a
    sentence-wide scan rejects it. cc-002 is that sentence.

    Tokens whose frame is n_a are not candidates, so a calendar year standing
    between a frame word and the quantity it describes does not absorb it.
    """
    frames = {e.frame for e in entries}
    if "n_a" in frames:
        return ""

    framed = _framed_positions(text, manifest)
    for word, frame in FRAME_WORDS.items():
        if frame in frames:
            continue
        for word_pos in find_in_sentence(text, pos, word):
            if nearest_position(framed, word_pos) == pos:
                return text[word_pos:word_pos + len(word)]
    return ""


def _reference_phrase(text: str, start: int, end: int) -> str:
    """The reference word and its number, as the explanation wrote them."""
    head = text[:start].rstrip()
    for word in REFERENCE_WORDS:
        if head.lower().endswith(word):
            return text[head.lower().rfind(word):end].strip()
    return text[start:end]


def check_membership(text: str, manifest) -> List[Finding]:
    """
    Every citable token must be a rendering the solver emitted.

    A string lookup, and nothing else. The renderings were enumerated at emit
    time precisely so this step never has to round.

    The candidate is canonicalized first, which is typography and not
    tolerance: `km² s⁻²` and `km^2/s^2` are one unit spelled two ways, and a
    U+2011 hyphen inside a date is the same date. See verify/normalize.py for
    why that is a separate module and why its tables are closed. Offsets in the
    findings below refer to the canonical text, which is the text every check
    here reads.
    """
    text = canonicalize(text)
    findings: List[Finding] = []
    index = manifest.index()
    citations = _citation_index(manifest)

    for token in extract(text):
        if token.classification == SPELLED_OUT:
            findings.append(Finding(
                token.text, "spelled-out-quantity", token.start,
                "a quantity written as words cannot be matched against a "
                "manifest rendering"))
            continue

        if token.classification == MALFORMED:
            findings.append(Finding(
                token.text, "unparseable", token.start,
                "not a number any reader or manifest can resolve"))
            continue

        if token.classification == REFERENCE:
            if token.text not in citations:
                # Name the whole reference. "3" is not the mistake; "Fig. 3" is.
                phrase = _reference_phrase(text, token.start, token.end)
                findings.append(Finding(
                    phrase, "label-disguise", token.start,
                    f"no manifest citation refers to {phrase}; a fabricated "
                    "reference standing beside a real value"))
            continue

        if token.classification != CITABLE:
            continue

        entries = index.get(token.text)
        if not entries:
            # One extra trailing digit is distinguishable from an invented
            # number by string alone: strip the trailing zeros and see whether
            # what remains is a rendering. No arithmetic, no comparison of
            # magnitudes, just characters.
            trimmed = token.text.rstrip("0") if "." in token.text else token.text
            if trimmed != token.text and trimmed.rstrip(".") in index:
                findings.append(Finding(
                    token.text, "precision-inflation", token.start,
                    f"the manifest renders this as {trimmed.rstrip('.')}, "
                    "claiming a digit the solver did not compute"))
            else:
                findings.append(Finding(
                    token.text, "fabricated-number", token.start,
                    "no manifest entry renders this value"))
            continue

        if token.unit:
            units = {e.unit for e in entries}
            if token.unit not in units:
                # The finding names the unit, because the unit is what is
                # wrong. The value is correct and reporting it as the offending
                # token would describe a mistake nobody made.
                written = raw_unit_text(text, token.end) or token.unit
                findings.append(Finding(
                    written, "wrong-unit", token.start,
                    f"{token.text} carries {written}, the manifest declares "
                    f"{sorted(units)}"))
                continue

        conflict = _frame_conflict(text, token.start, entries, manifest)
        if conflict:
            findings.append(Finding(
                conflict, "frame-mismatch", token.start,
                f"{token.text} is described as {conflict}, the manifest "
                f"declares {sorted({e.frame for e in entries})}"))

    return findings


# Every check the gate runs, in order. A check is added here only once it has
# a corpus case proving it rejects something and the accept suite proving it
# does not reject correct prose.
CHECKS = ("membership", "attribution")


def check(text: str, manifest) -> Verdict:
    """
    Run the gate over one explanation against one manifest.

    One manifest, one call. A number that is real but belongs to a different
    solve is not grounded here, and that is deliberate: `call_id` is what stops
    an explanation borrowing a plausible figure from a neighbouring run.
    """
    findings: List[Finding] = []
    findings.extend(check_membership(text, manifest))
    findings.extend(check_attribution(text, manifest))
    return Verdict(findings=findings, checks_run=CHECKS)
