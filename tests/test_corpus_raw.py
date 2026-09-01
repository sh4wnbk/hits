"""
tests/test_corpus_raw.py — the raw-submission schema, on its own terms.

BOB_BRIEF_CORPUS.md asks Bob for attack_shape and why, and asks it not to
assign a reason code. Nothing in the tree could load such a file, so the first
submission was written against the canonical loader instead: Bob found
expect_reason there and filled it in, and the corpus came back shaped by the
gate's own vocabulary. A schema with no loader is a schema an author routes
around, so the loader exists now.

Two properties are proved here.

Isolation. The raw validator must know no reason codes. That is checked by
walking the AST of the functions that implement it, not by reading them, so it
stays true as the module changes.

Separation. The canonical Case schema is not loosened to accept a raw case, and
a raw case cannot reach the runner by accident.
"""

import ast
import json
import os

import pytest

from verify import corpus
from verify.corpus import (
    ATTACK_SHAPES, RAW_FIELDS, RawCase, RawSubmissionError,
    load_raw_submission, load_cases, Case,
    ADVERSARIAL_FILE, GROUNDED_FILE, RAW_SUBMISSION_FILE,
)

MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "verify", "corpus.py")

# The names implementing the raw path. Everything reachable from these must be
# free of the gate's vocabulary.
RAW_IMPLEMENTATION = {"_parse_raw_case", "load_raw_submission", "RawCase",
                      "RawSubmissionError"}


def _valid_case(**overrides):
    text = "The C3 floor is 710 km^2/s^2, well above the published figure."
    case = {
        "case_id": "bob-001",
        "author": "bob",
        "created": "2026-08-29",
        "manifest_ref": "validate_full.json",
        "explanation": text,
        "expect": "reject",
        "attack_shape": "nudge",
        "offending_spans": [{"text": "710", "start": text.index("710"),
                             "end": text.index("710") + 3}],
        "why": "the floor is not this number; 710 reads as a loose rounding",
    }
    case.update(overrides)
    return case


def _write(tmp_path, *cases):
    p = tmp_path / "bob_submission.raw.jsonl"
    p.write_text("\n".join(json.dumps(c) for c in cases) + "\n", encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# 1. Isolation from the gate's vocabulary
# ---------------------------------------------------------------------------

def test_raw_validator_references_no_reason_code():
    """
    The raw path must not name REJECT_REASONS or any reason code.

    Walked from the AST rather than grepped, because verify/corpus.py legitimately
    contains the vocabulary for the canonical loader; the claim is about the raw
    functions specifically, not the file.
    """
    tree = ast.parse(open(MODULE_PATH, encoding="utf-8").read())
    vocabulary = set(corpus.REJECT_REASONS)
    offences = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            continue
        if node.name not in RAW_IMPLEMENTATION:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id == "REJECT_REASONS":
                offences.append(f"{node.name} line {sub.lineno}: REJECT_REASONS")
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if sub.value in vocabulary:
                    offences.append(
                        f"{node.name} line {sub.lineno}: reason code "
                        f"{sub.value!r}")

    assert not offences, (
        "the raw validator must know no reason codes; translation is the ingest "
        "pass's job:\n  " + "\n  ".join(offences))


def test_attack_shapes_are_the_briefs_nine():
    """Spelled as BOB_BRIEF_CORPUS.md spells them."""
    assert ATTACK_SHAPES == (
        "fabricate", "nudge", "wrong unit", "wrong frame", "disguise",
        "misattribute", "inflate", "spell out", "malform")


# ---------------------------------------------------------------------------
# 2. The schema
# ---------------------------------------------------------------------------

def test_valid_case_loads(tmp_path):
    cases = load_raw_submission(_write(tmp_path, _valid_case()))
    assert len(cases) == 1
    c = cases[0]
    assert isinstance(c, RawCase)
    assert c.attack_shape == "nudge"
    assert c.offending_spans[0].text == "710"
    assert not hasattr(c, "expect_reason")


def test_missing_file_is_empty_not_an_error(tmp_path):
    assert load_raw_submission(str(tmp_path / "absent.jsonl")) == []


def test_expect_reason_is_rejected_with_its_own_message(tmp_path):
    """
    The specific failure this loader exists to prevent, so it gets a message
    that explains the fix rather than a generic unknown-field complaint.
    """
    path = _write(tmp_path, _valid_case(expect_reason="plausible-rounding"))
    with pytest.raises(RawSubmissionError, match="does not assign one"):
        load_raw_submission(path)


def test_unknown_field_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(notes="a field the brief never asked for"))
    with pytest.raises(RawSubmissionError, match="not in the brief's schema"):
        load_raw_submission(path)


@pytest.mark.parametrize("field", sorted(RAW_FIELDS))
def test_each_required_field_is_required(tmp_path, field):
    case = _valid_case()
    del case[field]
    with pytest.raises(RawSubmissionError):
        load_raw_submission(_write(tmp_path, case))


def test_unknown_attack_shape_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(attack_shape="rounding"))
    with pytest.raises(RawSubmissionError, match="attack_shape"):
        load_raw_submission(path)


def test_accept_case_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(expect="accept"))
    with pytest.raises(RawSubmissionError, match="reject cases only"):
        load_raw_submission(path)


def test_non_bob_author_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(author="claude-code"))
    with pytest.raises(RawSubmissionError, match="black-box work"):
        load_raw_submission(path)


def test_empty_why_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(why="   "))
    with pytest.raises(RawSubmissionError, match="'why' is empty"):
        load_raw_submission(path)


def test_missing_span_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(offending_spans=[]))
    with pytest.raises(RawSubmissionError, match="no offending span"):
        load_raw_submission(path)


def test_span_offsets_are_verified(tmp_path):
    """
    The brief tells Bob not to verify offsets, so this does. A case whose span
    misses its token cannot show which token the gate caught.
    """
    path = _write(tmp_path, _valid_case(
        offending_spans=[{"text": "710", "start": 0, "end": 3}]))
    with pytest.raises(RawSubmissionError, match="span offsets do not match"):
        load_raw_submission(path)


def test_unknown_manifest_ref_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(manifest_ref="not_a_fixture.json"))
    with pytest.raises(RawSubmissionError, match="committed fixture"):
        load_raw_submission(path)


def test_duplicate_case_id_is_rejected(tmp_path):
    path = _write(tmp_path, _valid_case(), _valid_case())
    with pytest.raises(RawSubmissionError, match="duplicate case_id"):
        load_raw_submission(path)


# ---------------------------------------------------------------------------
# 3. Separation from the canonical corpus
# ---------------------------------------------------------------------------

def test_canonical_loader_still_rejects_a_raw_case(tmp_path):
    """
    The canonical schema is not loosened to accept Bob's. A raw case handed to
    the loader the tests read must fail, so the two cannot be confused.
    """
    p = tmp_path / "adversarial.jsonl"
    p.write_text(json.dumps(_valid_case()) + "\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_cases(str(p))


def test_raw_file_is_not_read_by_the_canonical_corpus():
    """
    load_all() reads the canonical files only, so the raw submission is
    invisible to the runner until the ingest pass has produced from it.
    """
    assert RAW_SUBMISSION_FILE not in (ADVERSARIAL_FILE, GROUNDED_FILE)
    src = open(os.path.join(os.path.dirname(MODULE_PATH), "corpus.py"),
               encoding="utf-8").read()
    load_all_body = src.split("def load_all()")[1].split("\ndef ")[0]
    assert "RAW_SUBMISSION_FILE" not in load_all_body
