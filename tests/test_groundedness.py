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

import os

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
        # Matched by containment, either direction, case-insensitively. Bob's
        # spans and the gate's findings name the same mistake at different
        # widths: a span may read "0.167 km/s" where the finding names the
        # "km/s" that is wrong, or "Fig. 3" where the gate names the reference
        # it could not find. Requiring equality would fail the gate for
        # describing the error more precisely than the case did. Containment
        # still fails a gate that tripped over an unrelated token, which is
        # what this assertion is for.
        flagged = {f.text.lower() for f in verdict.findings}
        expected = {s.text.lower() for s in case.offending_spans}
        overlap = any(f in e or e in f for f in flagged for e in expected)
        assert overlap, (
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


def test_typography_does_not_change_what_the_gate_accepts():
    """
    The live failure, end to end. Granite wrote `km² s⁻²` and a U+2011 hyphen
    inside an ISO date, and the gate rejected `km²`, `06` and `07` for a
    sentence in which every value was correct. Rejecting a real number for the
    shape of its glyph is not strictness, it is a wrong answer.

    The other half of the claim is in the same test: dressing a fabricated
    number in the same typography does not rescue it.
    """
    check = _gate()
    manifest = load_manifest_for(load_all()[0])
    index = manifest.index()
    c3 = "1331.16"
    assert c3 in index, "fixture changed; pick another computed rendering"

    typeset = f"The departure energy is {c3} km\u00b2 s\u207b\u00b2."
    assert check(typeset, manifest).grounded

    invented = "1331.17"
    assert invented not in index
    verdict = check(f"The departure energy is {invented} km\u00b2 s\u207b\u00b2.",
                    manifest)
    assert not verdict.grounded
    assert any(f.reason == "fabricated-number" for f in verdict.findings)


def test_word_units_ground_and_still_discriminate():
    """
    A reader who is not a mission designer does not read "km^2/s^2". The word
    forms are accepted so an explanation written for them is not rejected for
    its unit, and the two ways that could go wrong are asserted alongside:
    a wrong value in word units is still wrong, and a right value carrying the
    wrong word unit is still a unit mismatch.
    """
    check = _gate()
    manifest = load_manifest_for(load_all()[0])
    index = manifest.index()
    c3 = "1331.16"
    assert c3 in index and manifest.index()[c3][0].unit == "km^2/s^2"

    assert check(
        f"The departure energy is {c3} kilometres squared per second squared.",
        manifest).grounded

    invented = check(
        "The departure energy is 1331.17 kilometres squared per second squared.",
        manifest)
    assert not invented.grounded
    assert any(f.reason == "fabricated-number" for f in invented.findings)

    mismatched = check(
        f"The departure energy is {c3} kilometres per second.", manifest)
    assert not mismatched.grounded
    assert any(f.reason == "wrong-unit" for f in mismatched.findings)


def test_the_gate_reads_its_unit_spellings_from_the_manifest():
    """
    The manifest owns what a number may be written as. A synonym table defined
    inside the gate would be the gate granting itself that authority.
    """
    from solver.manifest import UNIT_SYNONYMS as source
    from verify import exemptions
    assert exemptions.UNIT_SYNONYMS is source
    assert exemptions.UNIT_LOOKAHEAD_CHARS > max(
        len(sp) for sps in source.values() for sp in sps)


DATE_CASES = [
    ("2030-09-20", True, "the ISO form, canonical"),
    ("September 20, 2030", True, "the human form, the other accepted rendering"),
    ("March 20, 2030", False, "a date the solver never emitted, whose 20 and "
                              "2030 are both grounded for unrelated reasons"),
    ("20 September 2030", False, "a third spelling of the right date"),
    ("Sep 20, 2030", False, "an abbreviated spelling of the right date"),
    ("September 20 2030", False, "the accepted form with its comma dropped, "
                                 "which is what Granite actually writes"),
]


@pytest.mark.parametrize("written,expected,why", DATE_CASES,
                         ids=[c[0] for c in DATE_CASES])
def test_a_date_is_matched_whole_or_not_at_all(written, expected, why):
    """
    The gate limit recorded in CLAUDE.md, closed and then watched staying
    closed.

    "September 20, 2030" used to pass on this manifest by accident: matched in
    pieces, its 20 is the twenty-year flight time and its 2030 is the departure
    year, both real renderings, so a wrong date could read as a right one. A
    date is now one token, looked up whole.

    Recognition is wider than acceptance on purpose. The manifest accepts two
    forms; the tokenizer recognises every date shape it can, so a third
    spelling arrives as one unmatched phrase rather than as digits that happen
    to be grounded elsewhere. Widening recognition only ever makes the gate
    stricter.
    """
    from solver.fetch import load_state_vectors
    from solver.intercept import intercept

    check = _gate()
    manifest = intercept("atlas", load_state_vectors(
        os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     "data", "state_vectors.json"))).manifest
    index = manifest.index()
    assert "20" in index and "2030" in index, (
        "this test is only meaningful while both fragments are independently "
        "grounded, which is what made the accident possible")

    verdict = check(f"The probe departs on {written}.", manifest)
    assert verdict.grounded is expected, (
        f"{written} ({why}): grounded={verdict.grounded}, "
        f"findings={[(f.text, f.reason) for f in verdict.findings]}")
    if not expected:
        assert any(f.text == written for f in verdict.findings), (
            "the whole date should be named as the offending token, not one "
            "of its digits")


def test_ordinary_prose_about_a_year_is_not_swallowed_as_a_date():
    """
    The cost of widening recognition, bounded. "The June 2027 launch" is
    ordinary writing about a grounded year, so no shape matches a month and a
    year without a day between them.
    """
    from verify.corpus_ingest import all_tokens
    assert [t[0] for t in all_tokens("The June 2027 launch cost 1400 km^2/s^2.")] == [
        "2027", "1400"]


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


# ---------------------------------------------------------------------------
# Dogfood: the solver's own printed rows, through the gate.
# ---------------------------------------------------------------------------

def test_the_printed_validation_rows_are_grounded(state_vectors, capsys):
    """
    Run the gate over the solver's own validation output.

    docs/MANIFEST.md, "The printed rows are bound to the manifest", says the
    print functions quote canonical renderings rather than carrying their own
    format specifiers, and that this test is what enforces it. Both
    print_frame_gate's docstring and validate()'s pointed here before the test
    existed, which is the drift this file is supposed to catch.

    What it buys: the rows a judge reads and the set of numbers an explanation
    may quote are the same strings. A format specifier reintroduced into a
    print function emits a token the manifest does not carry, and this goes
    red rather than the two quietly diverging.
    """
    check = _gate()
    from solver.validate import validate

    results = validate(state_vectors, verbose=True)
    printed = capsys.readouterr().out
    assert printed.strip(), "validate(verbose=True) printed nothing to gate"

    verdict = check(printed, results.manifest)
    assert verdict.grounded, (
        "the solver's own printed validation rows are not grounded against "
        "the manifest they were rendered from:\n  "
        + "\n  ".join(str(f) for f in verdict.findings))
