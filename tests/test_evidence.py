"""
tests/test_evidence.py — the evidence answers, and the claims they may not make.

These four answers are not gated the way object answers are, and that is a real
difference rather than an oversight: the gate checks numeric tokens against a
solver manifest, and there is no manifest for "Project Lyra exists". What
replaces the gate here is that every claim traces to a committed artefact and
every source is named in the response.

Which leaves two failure modes that no gate would catch, so they are asserted.

An evidence answer can contradict an accuracy guardrail. CLAUDE.md is explicit
that the gap is usability rather than availability, and that writing "no
software exists" is the specific error to avoid; E1's whole argument runs
alongside that line and could drift across it in a single edit.

And an evidence answer can let the two unvalidated objects borrow 'Oumuamua's
published-figure validation. That is the honesty seam of the entire project,
and E3 is the one place on the page where it is stated in prose.
"""

import json
import re
from pathlib import Path

import pytest

from app import chips

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = json.loads((REPO / "data" / "evidence.json").read_text())


def test_every_chip_has_an_answer_and_no_answer_lacks_a_chip():
    assert sorted(EVIDENCE) == sorted(chips.EVIDENCE_IDS)


def test_every_answer_names_its_sources():
    for eid, item in EVIDENCE.items():
        assert item["text"].strip(), eid
        assert item["sources"], eid
        for s in item["sources"]:
            assert s.strip() and len(s) > 10, (eid, s)


def test_no_evidence_answer_quotes_a_solver_figure():
    """
    The line held deliberately. Evidence prose is not gated, so a solver figure
    printed here would be the first ungated number on the site. Years and
    object designations are documentary and allowed; anything with a decimal
    point is not, because every quantity the solver emits carries one.
    """
    for eid, item in EVIDENCE.items():
        decimals = re.findall(r"\d+\.\d+", item["text"])
        assert not decimals, (
            f"{eid} quotes what looks like a solver figure: {decimals}. "
            "Evidence answers are not gated; describe the comparison and point "
            "at /gate/demo instead.")


def test_e1_does_not_claim_the_tools_are_unavailable():
    """
    CLAUDE.md's guardrail, asserted where it is most likely to be broken. GMAT
    and OITS are free and public, and the defensible claim is the narrower one
    about accessibility.
    """
    text = EVIDENCE["E1"]["text"].lower()
    for forbidden in ["no software exists", "no tool exists", "nothing exists",
                      "unavailable", "no one has studied", "nobody has studied"]:
        assert forbidden not in text, forbidden
    assert "usability, not availability" in text
    assert "gmat" in text and "oits" in text


def test_e1_counts_the_downloadable_tools_correctly():
    """
    E1 says OTIS is US-only and TRACE was never released. Two of the four are
    therefore downloadable by an arbitrary reader, and an earlier draft said
    three, contradicting its own two preceding sentences.
    """
    text = EVIDENCE["E1"]["text"]
    assert "Two of those four tools, GMAT and OITS" in text
    assert "Three of those four" not in text


def test_e1_ties_the_1960s_lineage_to_trace():
    """
    SSD-TDR-64-159 sources the 1960s date to The Aerospace Corporation's TRACE
    lineage, not to intercept mathematics in general. The sentence has to sit
    with TRACE or it is broader than its citation.
    """
    text = EVIDENCE["E1"]["text"]
    assert "1960s" in text
    trace_at = text.index("TRACE")
    sixties_at = text.index("1960s")
    assert trace_at < sixties_at, "the 1960s claim floated away from TRACE"
    assert sixties_at - trace_at < 220, (
        "the 1960s claim is no longer in TRACE's sentence")


def test_e1_oits_dependencies_match_the_committed_readme():
    """
    Fix landed on a source rather than on trimming. README.md names MATLAB, the
    SPICE toolkit and the NOMAD optimizer; E1 may name exactly those.
    """
    readme = (REPO / "README.md").read_text()
    assert "needs MATLAB, the SPICE toolkit" in readme
    assert "NOMAD optimizer" in readme
    text = EVIDENCE["E1"]["text"]
    for dep in ["MATLAB", "SPICE", "NOMAD"]:
        assert dep in text, dep


def test_e3_states_the_oumuamua_only_validation_plainly():
    """
    The single most important sentence on the page. Three objects are computed
    the same way and only one is validated against anything published, and a
    reader who came away thinking otherwise would have been misled by the count.
    """
    text = EVIDENCE["E3"]["text"]
    assert "2I/Borisov and 3I/ATLAS have no published intercept study" in text
    assert "nobody has published one" in text
    assert "do not inherit it" in text
    assert "patched-conic" in text


def test_e3_and_e4_point_at_the_live_gate_demo():
    for eid in ("E3", "E4"):
        assert "/gate/demo/oumuamua" in EVIDENCE[eid]["text"], eid


def test_e4_states_the_limit_that_grounding_is_not_truth():
    """
    CLAUDE.md: the gate certifies grounding, not truth. E4 is the answer most
    likely to be read as a guarantee of correctness, so it carries the limit.
    """
    text = EVIDENCE["E4"]["text"].lower()
    assert "does not certify that the sentence around the number is true" in text


def test_no_em_dashes_anywhere():
    """docs/CONVENTIONS.md and CLAUDE.md's writing rules."""
    for eid, item in EVIDENCE.items():
        assert "—" not in item["text"], eid
