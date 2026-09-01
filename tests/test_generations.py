"""
tests/test_generations.py — the committed Granite output stays checkable.

docs/generations/ holds the raw model output behind the claims in
BOB_USAGE.md and the README's "Where the AI can fall short" list. Its
README tells a reader to run the gate over those files and says what they will
see: three still grounded, and the one that invented a source paper now
rejected by the rule it prompted.

That instruction is a claim about current behaviour, so it is asserted here
rather than left as prose. If the gate changes and the source-paper case starts
passing again, this fails instead of the documentation quietly becoming false.

These are evidence, not answers. Nothing here is served, and the filenames sit
outside the closed key set so a stray copy into data/answers/ is caught by
tests/test_answers.py rather than reaching a reader.
"""

import glob
import json
import os

import pytest

from solver import objects
from solver.frozen import load
from verify.groundedness import check

DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "generations")

FILES = sorted(glob.glob(os.path.join(DIR, "*.json")))

# What each file is evidence of. The README table says the same thing in prose,
# and a reader who trusts neither can run the gate themselves.
EXPECTED = {
    "2026-08-31-borisov-target-planet.json": True,
    "2026-08-31-borisov-could-intercept.json": True,
    "2026-08-31-oumuamua-could-reach.json": True,
    # Rejected by the rule this file is the reason for.
    "2026-08-31-borisov-source-paper.json": False,
}


def test_the_evidence_is_still_there():
    assert {os.path.basename(f) for f in FILES} == set(EXPECTED), (
        "docs/generations/ no longer matches what its README and "
        "BOB_USAGE.md describe")


@pytest.mark.parametrize("path", FILES, ids=os.path.basename)
def test_each_generation_reads_as_a_real_one(path):
    """
    They keep the CachedAnswer shape, which is what makes them checkable by the
    same code that reads a served answer.
    """
    d = json.load(open(path, encoding="utf-8"))
    assert d["object_key"] in objects.KEYS
    assert d["served_by"] in ("granite_first_pass", "granite_after_regen")
    assert d["model_id"], "a generation with no model is not a generation"
    assert d["text"].strip()


@pytest.mark.parametrize("path", FILES, ids=os.path.basename)
def test_the_gate_still_says_what_the_record_says_it_says(path):
    """
    The point of keeping these. Three grounded answers that were wrong anyway,
    which is the README's argument that grounded is not correct, and one that
    the gate has since learned to catch.
    """
    d = json.load(open(path, encoding="utf-8"))
    verdict = check(d["text"], load(d["object_key"]).manifest)
    expected = EXPECTED[os.path.basename(path)]
    assert verdict.grounded is expected, (
        f"{os.path.basename(path)}: expected grounded={expected}, got "
        f"{verdict.grounded} {[(f.text, f.reason) for f in verdict.findings]}")

    if not expected:
        assert any(f.reason == "unsourced-attribution"
                   for f in verdict.findings), verdict.findings


def test_none_of_the_evidence_is_named_like_a_servable_answer():
    """
    data/answers/{key}.json is what gets served. These deliberately do not match
    that shape, so a copy into that directory fails
    test_the_answer_directory_holds_nothing_but_the_closed_set rather than
    reaching a reader as an answer.
    """
    for path in FILES:
        stem = os.path.basename(path)[: -len(".json")]
        assert stem not in objects.KEYS, stem
