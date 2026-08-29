"""
tests/test_template.py — the deterministic explanation floor.

Two claims, and they are different claims.

The first is behavioural: run the gate over the floor's own output and it comes
back grounded. That is the exit condition, and it is watched rather than
argued, because CLAUDE.md is explicit that an explanation of what the code does
is a hypothesis until executed.

The second is structural: the floor has no way to produce a number that is not
a manifest rendering, because it cannot format, round, or compute one. The AST
walk below is the same instrument as
tests/test_groundedness.py::test_gate_does_no_arithmetic, pointed at the other
end of the path. Together they say the manifest is the only place a number can
enter an explanation and the only place one can be rounded.
"""

import ast
import os

import pytest

from agent import template
from solver.manifest import Manifest, from_solve_result
from solver.solve import solve
from verify.groundedness import check

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "manifests",
                       "validate_full.json")

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "agent", "template.py")


@pytest.fixture(scope="module")
def validate_manifest():
    """The frozen 81-entry manifest for a full validate() call."""
    with open(FIXTURE, encoding="utf-8") as fh:
        return Manifest.from_json(fh.read())


@pytest.fixture(scope="module")
def solve_manifest(state_vectors):
    """
    A manifest for one real solve: the Sample A transfer, computed here.

    A real solve rather than a frozen fixture, because the intercept template
    is the shape a user actually hits and its numbers should be the ones the
    solver produces today, not ones pinned alongside the template that wrote
    them.
    """
    result = solve(state_vectors["earth_sample_ab_launch"],
                   state_vectors["oumuamua_sample_a_arrival"],
                   tof_days=365.0)
    return from_solve_result(result)


# ---------------------------------------------------------------------------
# The floor passes its own gate
# ---------------------------------------------------------------------------

def test_validation_summary_is_grounded(validate_manifest):
    text = template.explain(validate_manifest)
    verdict = check(text, validate_manifest)
    assert verdict.grounded, (
        "the deterministic floor spoke a number its own manifest does not "
        "render:\n  " + "\n  ".join(
            f"{f.reason}: {f.text!r} — {f.note}" for f in verdict.findings))
    assert "membership" in verdict.checks_run


def test_intercept_answer_is_grounded(solve_manifest):
    text = template.explain(solve_manifest)
    verdict = check(text, solve_manifest)
    assert verdict.grounded, (
        "the deterministic floor spoke a number its own manifest does not "
        "render:\n  " + "\n  ".join(
            f"{f.reason}: {f.text!r} — {f.note}" for f in verdict.findings))
    assert "membership" in verdict.checks_run


def test_both_shapes_quote_the_numbers_that_matter(validate_manifest,
                                                   solve_manifest):
    """
    Grounded is not the same as useful. An empty string is grounded.

    So the headline quantities are asserted present: the floor has to be an
    explanation someone can act on, not merely one the gate cannot fault.
    """
    summary = template.explain(validate_manifest)
    for entry_id in ("validate.frame_gate.computed",
                     "validate.frame_gate.published",
                     "validate.c3.floor.computed",
                     "validate.c3.floor.published",
                     "validate.arrival_a.v_inf2"):
        rendering = validate_manifest.canonical(entry_id)
        assert rendering in summary, f"{entry_id} ({rendering}) not explained"

    intercept = template.explain(solve_manifest)
    for entry_id in ("solve.c3", "solve.dv_depart", "solve.v_inf2",
                     "solve.tof_days"):
        rendering = solve_manifest.canonical(entry_id)
        assert rendering in intercept, f"{entry_id} ({rendering}) not explained"


def test_fidelity_limit_is_stated_in_every_shape(validate_manifest,
                                                 solve_manifest):
    """
    CLAUDE.md: state the fidelity limits wherever a number is presented as
    authoritative. The floor is where a number is presented with no model in
    the path at all, which is the most authoritative it ever looks.
    """
    for manifest in (validate_manifest, solve_manifest):
        text = template.explain(manifest)
        assert "patched-conic" in text
        assert "n-body" in text


def test_dispatch_refuses_a_manifest_it_has_no_template_for(validate_manifest):
    validate_manifest.producer = "grid"
    with pytest.raises(ValueError, match="no deterministic template"):
        template.explain(validate_manifest)
    validate_manifest.producer = "validate"


def test_a_shape_refuses_the_wrong_producer(solve_manifest):
    """
    The intercept template on a validate manifest would raise KeyError deep in
    Manifest.by_id. It fails at the door instead, so the message names the
    mistake rather than the first entry id that happened to be missing.
    """
    with pytest.raises(ValueError, match="wants a validate manifest"):
        template.explain_validation(solve_manifest)


# ---------------------------------------------------------------------------
# The structural claim
# ---------------------------------------------------------------------------

def test_template_never_formats_a_number():
    """
    The floor cannot round, compute, or format a value into a string.

    If it could, there would be two rounding policies: the ladder in
    solver/manifest.py, which the gate's membership test is built around, and
    whatever a format specifier here did. The first time they disagreed the
    floor would emit a string the gate rejects, and the fallback path would be
    the one thing in the system that cannot be served.

    Add is permitted, because it concatenates strings and the module holds no
    numbers to add. Sub, Mult, Div, FloorDiv and Pow are not, and neither is
    any format specifier, %-formatting, or a call that turns a value into a
    numeral.
    """
    tree = ast.parse(open(TEMPLATE_PATH, encoding="utf-8").read())
    banned_calls = {"float", "round", "abs", "int", "complex", "pow", "divmod",
                    "format"}
    banned_modules = {"math", "numpy", "np", "decimal", "fractions",
                      "statistics"}
    offences = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in banned_calls:
                offences.append(f"line {node.lineno}: calls {node.func.id}()")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("format", "__format__"):
                offences.append(f"line {node.lineno}: calls .{node.func.attr}()")
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
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            offences.append(f"line {node.lineno}: %-formatting or modulo")
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            offences.append(f"line {node.lineno}: f-string format specifier")
        if isinstance(node, ast.Constant) and isinstance(
                node.value, (int, float)) and not isinstance(node.value, bool):
            offences.append(f"line {node.lineno}: numeric literal "
                            f"{node.value!r}")

    assert not offences, (
        "the floor must not produce a number of its own. Offences:\n  "
        + "\n  ".join(offences))


def test_every_number_in_the_floor_is_a_manifest_rendering(validate_manifest,
                                                           solve_manifest):
    """
    The membership claim stated directly, without going through the gate.

    check() is the instrument under test elsewhere in this suite, so the floor's
    central property is also asserted against the manifest index itself: every
    citable token the extractor finds in the floor's prose is a string some
    entry declared.
    """
    from verify.extract import CITABLE, extract

    for manifest in (validate_manifest, solve_manifest):
        index = manifest.index()
        text = template.explain(manifest)
        for token in extract(text):
            if token.classification != CITABLE:
                continue
            assert token.text in index, (
                f"{token.text!r} at {token.start} is not a rendering of any "
                f"entry in the {manifest.producer} manifest")
