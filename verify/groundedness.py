"""
verify/groundedness.py — the deterministic groundedness gate.

Built in pieces, against the corpus, in the order the corpus proves each piece
is needed. This file currently holds ONE check, and `Verdict.checks_run` says
so on every verdict it returns. A grounded verdict from this module today means
"the attribution check found nothing", NOT "every number is grounded". The
membership test and the extraction rule are not written yet, and until they
are, the 23 membership cases in the corpus fail as accepted-but-should-reject.
That red is the honest report of what is missing.

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
)

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

    return findings


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


# Every check the gate runs, in order. A check is added here only once it has
# a corpus case proving it rejects something and the accept suite proving it
# does not reject correct prose.
CHECKS = ("attribution",)


def check(text: str, manifest) -> Verdict:
    """
    Run the gate over one explanation against one manifest.

    One manifest, one call. A number that is real but belongs to a different
    solve is not grounded here, and that is deliberate.
    """
    findings: List[Finding] = []
    findings.extend(check_attribution(text, manifest))
    return Verdict(findings=findings, checks_run=CHECKS)
