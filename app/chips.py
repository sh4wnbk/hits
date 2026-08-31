"""
app/chips.py — the questions the page offers, and where each came from.

Data, not prose. Every chip on the page is declared here with the mined text it
was drawn from and the thing that answers it, so the page cannot grow a question
HITS does not answer without this file saying so first.

## Why provenance rides on the chip

docs/chip_candidates.md records that the best-phrased question in the corpus,
"Can we intercept it with a probe?", is one HITS refuses to answer: it asks for
a feasibility verdict, and HITS computes what a transfer costs and has no
launcher model with which to judge it. The decision taken there was to recast
the label to the cost question and keep the mined question beside it as
provenance. That separation is structural here rather than editorial: `label`
is what the chip says, `mined` is what someone actually asked, and the two are
different fields so a later edit cannot quietly promote the mined text into the
label.

## Why the corpus figure on the page is 494 and not 3,171

The chips were drawn from the interstellar-object subset, 494 questions across
oumuamua.txt, 3iatlas_known.txt and 3iatlas_mars.txt. The full corpus is 3,171
questions, but most of it is about Mars rovers and TRAPPIST-1, which HITS does
not compute for. Quoting the larger number beside these chips would be
borrowing weight from questions that had no bearing on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

# The corpus figures the page is allowed to state. Both are checked by
# tests/test_chips.py against a re-run of the extraction rule, so neither can go
# stale the way the 14,293 figure did (CLAUDE.md, the evidence corpus guardrail).
CORPUS_QUESTIONS_TOTAL = 3171
CORPUS_QUESTIONS_INTERSTELLAR = 494
CORPUS_COMMENTS = 19122
CORPUS_VIDEOS = 6

CORPUS_NOTE = (
    f"The questions below are drawn from the {CORPUS_QUESTIONS_INTERSTELLAR} "
    f"interstellar-object questions in the corpus, not from all "
    f"{CORPUS_QUESTIONS_TOTAL}. The rest ask about Mars rovers and TRAPPIST-1, "
    "which HITS does not compute for."
)


@dataclass(frozen=True)
class ObjectFacet:
    """
    One question shape an object's answer covers.

    `entry_ids` names the manifest entries that answer it. It is not decoration:
    a facet claiming to answer a question with a number the manifest does not
    hold is the failure this field makes visible, and tests/test_chips.py
    checks every id against all three committed manifests.
    """
    key: str
    label: str
    entry_ids: Tuple[str, ...]
    mined: str = ""
    mined_source: str = ""
    note: str = ""


@dataclass(frozen=True)
class EvidenceChip:
    """One question about the tool itself, answered from a committed artefact."""
    eid: str
    label: str
    mined: str
    mined_source: str


# The four facets an object answer covers. Ordered as a reader meets them:
# how long, what it costs, how fast, when.
OBJECT_FACETS: Tuple[ObjectFacet, ...] = (
    ObjectFacet(
        key="O1",
        label="How long would the flight take?",
        entry_ids=("solve.tof_days", "solve.tof_years"),
        mined="how long will it take us to get there?",
        mined_source="cluster 45",
    ),
    ObjectFacet(
        key="O2",
        label="What would it cost to launch?",
        entry_ids=("solve.c3", "solve.dv_depart"),
        mined="Can we intercept it with a probe?",
        mined_source="cluster 42",
        note=(
            "Asked as a cost, not as a verdict. HITS computes what the transfer "
            "costs and does not model launcher capability, so it cannot say "
            "whether the cost could be met. Cost here is launch energy, not "
            "money."
        ),
    ),
    ObjectFacet(
        key="O3",
        label="How fast would the probe pass it?",
        entry_ids=("solve.v_arr", "solve.v_inf2"),
        mined=("Do we even have anything that could intercept that?, even if we "
               "knew it was coming like 10 years ago?"),
        mined_source="oumuamua.txt",
    ),
    ObjectFacet(
        key="O4",
        label="When would it have to launch?",
        entry_ids=("solve.departure.iso", "solve.arrival.iso"),
        mined=("Are we going to go send a probe there? If so, when is the right "
               "time to do so?"),
        mined_source="cluster 42",
        note=(
            "The departure epoch of a committed transfer. HITS does not search "
            "for the best launch date at request time."
        ),
    ),
)

EVIDENCE_CHIPS: Tuple[EvidenceChip, ...] = (
    EvidenceChip(
        eid="E1",
        label="Why has nobody gone after it?",
        mined=("Why isn't there spacecraft waiting to intercept any "
               "interstellar objects for scientific purposes?"),
        mined_source="3iatlas_known.txt",
    ),
    EvidenceChip(
        eid="E2",
        label="Has anyone studied this seriously?",
        mined="Surely we are going to want to send a probe to sample materials?",
        mined_source="oumuamua.txt",
    ),
    EvidenceChip(
        eid="E3",
        label="How do we know the numbers are right?",
        mined="3rd object ever? How do we know?",
        mined_source="3iatlas_mars.txt",
    ),
    EvidenceChip(
        eid="E4",
        label="Could the AI be inventing these?",
        mined="How do you know? Theory?",
        mined_source="oumuamua.txt",
    ),
)

EVIDENCE_IDS = tuple(c.eid for c in EVIDENCE_CHIPS)


def facet(key: str) -> ObjectFacet:
    for f in OBJECT_FACETS:
        if f.key == key:
            return f
    raise KeyError(key)


def evidence_chip(eid: str) -> EvidenceChip:
    for c in EVIDENCE_CHIPS:
        if c.eid == eid:
            return c
    raise KeyError(eid)
