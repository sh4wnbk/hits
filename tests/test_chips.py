"""
tests/test_chips.py — the page's questions, and the claims it is allowed to make.

Two failures this guards against, both of which would be invisible in a browser.

A facet can claim to answer a question with a number the manifest does not
hold. `entry_ids` exists to make that checkable, and it is only worth having if
something checks it, so every id is looked up in all three committed manifests.

And a chip label can quietly become a question HITS refuses to answer.
docs/chip_candidates.md records the decision on the sharpest case: the mined
"Can we intercept it with a probe?" asks for a feasibility verdict, HITS gives
none, so the label is the cost question and the mined text rides beside it as
provenance. That separation lives in two dataclass fields, and a test asserts
the mined text never becomes the label.
"""

import re
from pathlib import Path

import pytest

from app import chips
from solver import objects
from solver.frozen import load_all

MIN_WORDS = 4
CORPUS_FILES = ["curiosity_animation.txt", "trappist1.txt", "7min_terror.txt",
                "oumuamua.txt", "3iatlas_known.txt", "3iatlas_mars.txt"]
INTERSTELLAR_FILES = ["oumuamua.txt", "3iatlas_known.txt", "3iatlas_mars.txt"]
DATA = Path(__file__).resolve().parent.parent / "data"


def _questions(files):
    """The extraction rule from data/cluster_questions.py, applied here."""
    out = []
    for f in files:
        for line in (DATA / f).read_text(encoding="utf-8", errors="replace").splitlines():
            t = re.sub(r"^\d+\.\s*", "", line).strip()
            if "?" in t and len(t.split()) >= MIN_WORDS:
                out.append(t)
    return out


# ---------------------------------------------------------------------------
# The corpus figures the page prints
# ---------------------------------------------------------------------------

def test_the_corpus_counts_the_page_states_are_the_counts_in_the_corpus():
    """
    Both figures are recomputed, not trusted.

    CLAUDE.md records this exact number going stale once: docs/EVIDENCE.md said
    14,293 comments until counting the committed files showed otherwise. A
    figure printed on a public page is the worst place for that to happen
    again, so the page's numbers are checked against a re-run of the extraction
    rule rather than against a constant someone remembered to update.
    """
    assert len(_questions(CORPUS_FILES)) == chips.CORPUS_QUESTIONS_TOTAL
    assert len(_questions(INTERSTELLAR_FILES)) == chips.CORPUS_QUESTIONS_INTERSTELLAR


def test_the_corpus_note_quotes_the_smaller_figure_as_the_source():
    """
    The chips were drawn from the interstellar subset. Presenting them under
    the full 3,171 would borrow weight from questions about Mars rovers that
    had no bearing on any of them.
    """
    note = chips.CORPUS_NOTE
    assert str(chips.CORPUS_QUESTIONS_INTERSTELLAR) in note
    assert str(chips.CORPUS_QUESTIONS_TOTAL) in note
    assert note.index(str(chips.CORPUS_QUESTIONS_INTERSTELLAR)) < \
           note.index(str(chips.CORPUS_QUESTIONS_TOTAL))


# ---------------------------------------------------------------------------
# Facets answer with numbers that exist
# ---------------------------------------------------------------------------

def test_every_facet_entry_id_exists_in_every_committed_manifest():
    """
    A facet claiming a number the manifest does not hold would render an empty
    promise on the page and would only be noticed by someone who clicked.
    """
    manifests = {fi.key: fi.manifest for fi in load_all()}
    assert set(manifests) == set(objects.KEYS)
    for f in chips.OBJECT_FACETS:
        assert f.entry_ids, f.key
        for entry_id in f.entry_ids:
            for key, m in manifests.items():
                m.by_id(entry_id)      # KeyError if absent


def test_the_four_facets_are_the_picked_set():
    assert tuple(f.key for f in chips.OBJECT_FACETS) == ("O1", "O2", "O3", "O4")
    assert tuple(c.eid for c in chips.EVIDENCE_CHIPS) == ("E1", "E2", "E3", "E4")


# ---------------------------------------------------------------------------
# The provenance separation
# ---------------------------------------------------------------------------

def test_no_mined_question_is_used_as_a_label():
    """
    The structural half of the decision in docs/chip_candidates.md. A chip that
    asks "can we" and returns a number reads as a yes, and HITS gives no
    feasibility verdict.
    """
    for f in chips.OBJECT_FACETS:
        if f.mined:
            assert f.label != f.mined, f.key
    for c in chips.EVIDENCE_CHIPS:
        assert c.label != c.mined, c.eid


def test_the_feasibility_question_is_provenance_and_the_label_is_the_cost():
    """
    The specific case, asserted by name rather than by rule, because it is the
    one a later edit is most likely to undo.
    """
    o2 = chips.facet("O2")
    assert o2.mined == "Can we intercept it with a probe?"
    assert "cost" in o2.label.lower()
    assert "can we" not in o2.label.lower()
    assert "launcher capability" in o2.note
    assert "not money" in o2.note


def test_no_label_asks_for_a_verdict_hits_does_not_give():
    """
    A blunt guard over every label, not just O2. HITS reports what a transfer
    costs; a label promising feasibility would be promising something the
    template explicitly refuses to say.
    """
    forbidden = ["can we catch", "can we reach", "is it possible",
                 "could we build", "is it feasible", "will we"]
    for f in chips.OBJECT_FACETS:
        low = f.label.lower()
        for phrase in forbidden:
            assert phrase not in low, (f.key, f.label)


# ---------------------------------------------------------------------------
# Every mined string is real
# ---------------------------------------------------------------------------

def test_every_mined_question_is_verbatim_corpus_text():
    """
    The chips claim to come from what people actually asked. If a quotation has
    been tidied, that claim is false, and it is the sort of false that nobody
    notices. Whitespace is normalised on both sides because the page wraps;
    words and punctuation are not.
    """
    flat = re.sub(r"\s+", " ", "\n".join(
        (DATA / f).read_text(encoding="utf-8", errors="replace")
        for f in CORPUS_FILES))
    mined = [(f.key, f.mined) for f in chips.OBJECT_FACETS if f.mined]
    mined += [(c.eid, c.mined) for c in chips.EVIDENCE_CHIPS]
    assert len(mined) == 8
    for key, q in mined:
        probe = re.sub(r"\s+", " ", q).strip()
        assert probe in flat, f"{key}: not verbatim corpus text: {probe!r}"
