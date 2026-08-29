"""
tests/test_groundedness.py — the groundedness gate, run against the corpus.

This file exists BEFORE the gate does, and that ordering is the point. A gate
is not trusted because its author reasoned correctly about it; it is trusted
because a fabricated number was watched getting rejected. CLAUDE.md puts it
plainly: no solver behaviour is believed until a test or a plot demonstrates
it, and an explanation of what the code does is a hypothesis until executed.

So the expected state of this file on the commit that introduces it is RED.
It fails because verify.groundedness does not exist. When the gate lands, these
same tests go green without being edited.

Corpus format and authorship split: docs/CORPUS.md.
  tests/corpus/adversarial.jsonl  reject cases, authored black-box by Bob
  tests/corpus/grounded.jsonl     accept cases, authored white-box here
"""

import pytest

from verify.corpus import (
    load_cases, load_all, load_manifest_for,
    ADVERSARIAL_FILE, GROUNDED_FILE, REJECT_REASONS,
)

# Coverage bars from docs/CORPUS.md. A corpus below them is not evidence.
#
# The reject floor is 23, not 30. Bob's submission was 35 cases, and the ingest
# pass resolved it into 23 rejections plus 9 documented limits in
# known_limits.jsonl (7 attribution-seam, 2 result-binding) with 3 quarantined.
# The original 30 assumed every case Bob wrote would be a rejection. Nine were
# not: frozen membership accepts them, because the token is in the manifest with
# a matching unit and frame and the wrongness is in what the number is attached
# to. Counting those toward a rejection floor would credit the gate with catches
# it does not make, so the bar tracks what the gate can actually catch.
#
# It moved back to 30 when the attribution check landed. Seven of the nine
# limits were the published/computed seam, which IS decidable from entry.kind
# plus a phrase list, and verify.groundedness.check_attribution now decides it,
# so they are rejections again. The remaining two, bob-027 and bob-033, stay in
# known_limits.jsonl: they turn on which result a number is attached to, which
# no manifest metadata encodes, and they are the honest record of what this
# gate still cannot see.
MIN_REJECT_CASES = 30
MIN_ACCEPT_CASES = 12
MIN_REASON_CATEGORIES = 8


def _gate():
    """
    Import the gate, or fail with the reason rather than an opaque ImportError.

    Kept out of module scope on purpose: a missing gate must fail the tests that
    exercise it, not collapse collection for the corpus-shape tests, which are
    meaningful on their own and are what Bob's work is checked against.
    """
    try:
        from verify.groundedness import check
    except ImportError as exc:
        pytest.fail(
            "verify.groundedness.check does not exist yet.\n"
            "This is the expected state until the gate is built: the corpus and "
            "this runner are the first artifact, the gate is written against "
            f"them, and these tests are what turns green.\n  ({exc})")
    return check


# ---------------------------------------------------------------------------
# Corpus shape. Meaningful with or without the gate.
# ---------------------------------------------------------------------------

def test_corpus_loads():
    """Every case satisfies docs/CORPUS.md, including span offsets."""
    cases = load_all()
    assert cases, "no corpus cases at all"


def test_accept_corpus_meets_its_bar():
    cases = load_cases(GROUNDED_FILE)
    assert len(cases) >= MIN_ACCEPT_CASES, (
        f"{len(cases)} accept cases, need {MIN_ACCEPT_CASES}. Without them a "
        "gate that rejects everything would satisfy the whole reject corpus.")
    assert all(c.author == "claude-code" for c in cases), (
        "accept cases are authored white-box; a black-box author cannot write a "
        "guaranteed-pass case for a rule they have not been shown")


def test_reject_corpus_meets_its_bar():
    cases = load_cases(ADVERSARIAL_FILE)
    assert len(cases) >= MIN_REJECT_CASES, (
        f"{len(cases)} reject cases, need {MIN_REJECT_CASES}. "
        f"Brief: docs/BOB_BRIEF_CORPUS.md")
    assert all(c.author == "bob" for c in cases), (
        "reject cases are authored black-box by Bob; the independence is what "
        "makes a rejection worth something")
    reasons = {c.expect_reason for c in cases}
    assert len(reasons) >= MIN_REASON_CATEGORIES, (
        f"reject cases span {len(reasons)} reason categories, need "
        f"{MIN_REASON_CATEGORIES}. Present: {sorted(reasons)}. "
        f"Missing: {sorted(set(REJECT_REASONS) - reasons)}")


def test_every_case_names_a_committed_manifest():
    for case in load_all():
        assert load_manifest_for(case).entries, (
            f"{case.case_id}: manifest {case.manifest_ref} has no entries")


# ---------------------------------------------------------------------------
# The gate itself.
# ---------------------------------------------------------------------------

def _all_cases():
    try:
        return load_all()
    except Exception:
        return []


def _case_id(case):
    return case.case_id


@pytest.mark.parametrize("case", _all_cases(), ids=_case_id)
def test_case(case):
    """
    One corpus case. A reject must be rejected, for the stated reason, at the
    stated span; an accept must be accepted.

    The span check is not pedantry. A gate that rejects a fabricated
    explanation because it tripped over an unrelated token has not caught the
    attack, and without checking the span that failure looks identical to a
    success.
    """
    check = _gate()
    manifest = load_manifest_for(case)
    verdict = check(case.explanation, manifest)

    if case.is_reject:
        assert not verdict.grounded, (
            f"{case.case_id} was ACCEPTED but must be rejected "
            f"({case.expect_reason}). {case.notes}\n"
            f"  explanation: {case.explanation!r}")
        flagged = {f.text for f in verdict.findings}
        expected = {s.text for s in case.offending_spans}
        assert expected & flagged, (
            f"{case.case_id} was rejected, but not for the right token. "
            f"expected one of {sorted(expected)}, gate flagged {sorted(flagged)}")
        reasons = {f.reason for f in verdict.findings}
        assert case.expect_reason in reasons, (
            f"{case.case_id} rejected for {sorted(reasons)}, "
            f"expected {case.expect_reason}")
    else:
        assert verdict.grounded, (
            f"{case.case_id} was REJECTED but is fully grounded. {case.notes}\n"
            f"  findings: {[(f.text, f.reason) for f in verdict.findings]}")


def test_gate_does_no_arithmetic():
    """
    The guarantee, made checkable instead of promised.

    If the gate can re-derive 1.62% from 714.36 and 703, then what it certifies
    is that it can do arithmetic, not that the explanation is grounded. This
    walks the AST of the matching path and fails on any numeric conversion,
    rounding, absolute value, or arithmetic on candidate values.
    """
    import ast
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "verify", "groundedness.py")
    if not os.path.exists(path):
        pytest.fail(
            "verify/groundedness.py does not exist yet. Expected until the "
            "gate is built.")

    tree = ast.parse(open(path).read())
    banned_calls = {"float", "round", "abs", "int", "complex", "pow", "divmod"}
    banned_modules = {"math", "numpy", "np", "decimal", "fractions", "statistics"}
    offences = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in banned_calls:
                offences.append(f"line {node.lineno}: calls {node.func.id}()")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", None) or ""
            names = [a.name for a in node.names]
            if mod.split(".")[0] in banned_modules or any(
                    n.split(".")[0] in banned_modules for n in names):
                offences.append(f"line {node.lineno}: imports {mod or names}")
        if isinstance(node, ast.BinOp) and isinstance(
                node.op, (ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)):
            offences.append(
                f"line {node.lineno}: arithmetic {type(node.op).__name__}")

    assert not offences, (
        "the gate must not compute. Offences:\n  " + "\n  ".join(offences))
