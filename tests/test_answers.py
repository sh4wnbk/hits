"""
tests/test_answers.py — every committed answer, re-gated.

app/answers.py says this file exists and says what it does: `load()` does not
re-check grounding, `verified_grounded` is recorded at freeze time rather than
recomputed, and the reason that is safe is that CI runs the gate over every
committed answer against that object's committed manifest. The file did not
exist. The docstring was a promise, which is the divergence CLAUDE.md names as
this repository's most likely failure: a document describing something the code
does not do.

It matters at exactly one moment, and that moment is not the freeze. An answer
is generated against a manifest and frozen with it agreeing. If the manifest is
later refrozen, from new ephemerides or a corrected transfer, the numbers in the
prose become numbers the solver no longer emits, and nothing about the answer
file changes to say so. Without this, that answer keeps being served, still
labelled grounded, still carrying the verdict of a check that was run against a
manifest that is gone.

So the gate runs here, over what is committed, not over what was generated.
"""

import json
import os

import pytest

from app import answers as answer_store
from solver import objects
from solver.frozen import load
from verify.groundedness import check

SERVED_BY = ("granite_first_pass", "granite_after_regen", "deterministic_floor")

COMMITTED = [k for k in objects.KEYS
             if os.path.exists(answer_store.path_for(k))]


def test_the_answer_directory_holds_nothing_but_the_closed_set():
    """
    A stray file here is served to a reader as an object's answer. The set of
    objects is closed, so the set of answers is too.
    """
    if not os.path.isdir(answer_store.ANSWER_DIR):
        pytest.skip("no answers frozen yet")
    found = {f[:-len(".json")] for f in os.listdir(answer_store.ANSWER_DIR)
             if f.endswith(".json")}
    assert found <= set(objects.KEYS), (
        f"{sorted(found - set(objects.KEYS))} is not one of {list(objects.KEYS)}")


@pytest.mark.parametrize("key", COMMITTED)
def test_a_committed_answer_still_passes_the_gate(key):
    """
    The promise in app/answers.py, kept. Run against the committed manifest
    rather than the one the generation saw, because those are the same file
    only until someone refreezes it.
    """
    cached = answer_store.load(key)
    verdict = check(cached.text, load(key).manifest)
    assert verdict.grounded, (
        f"the committed answer for {key} no longer grounds against "
        f"data/manifests/{key}.json: "
        + "; ".join(f"{f.reason} {f.text!r}" for f in verdict.findings))


@pytest.mark.parametrize("key", COMMITTED)
def test_a_committed_answer_is_bound_to_the_call_it_explains(key):
    """
    The call_id ties the prose to one solver run. An answer carrying a
    different one is an answer about a computation this deployment does not
    serve, however well its numbers happen to match.
    """
    assert answer_store.load(key).call_id == load(key).call_id


@pytest.mark.parametrize("key", COMMITTED)
def test_a_committed_answer_is_about_the_object_it_is_filed_under(key):
    """
    Two of the three objects share a flight time and an order of magnitude, so
    a file written under the wrong key is not something a reader would catch.
    The gate would: an answer only grounds against its own manifest.
    """
    cached = answer_store.load(key)
    frozen = load(key)
    assert cached.object_key == key
    assert frozen.designation in cached.text

    for other in objects.KEYS:
        if other == key:
            continue
        assert not check(cached.text, load(other).manifest).grounded, (
            f"the answer filed as {key} also grounds against {other}, so the "
            "two are not distinguishable by the gate")


@pytest.mark.parametrize("key", COMMITTED)
def test_a_committed_answer_says_which_path_produced_it(key):
    """
    CLAUDE.md forbids an offline result being mis-credited to the credentialed
    system. A frozen file is where that would happen silently, so the fields
    are held apart: a floor names no model, and a Granite answer names one and
    says when it was called.
    """
    cached = answer_store.load(key)
    assert cached.served_by in SERVED_BY, cached.served_by
    assert cached.verified_grounded is True
    assert cached.generated_at

    if cached.served_by == "deterministic_floor":
        assert cached.model_id == "", (
            f"{key} is frozen as the floor but names a model, which is the "
            "mis-crediting the field exists to prevent")
        assert cached.regenerations == 0
        assert not cached.from_granite
    else:
        assert cached.model_id, key
        assert cached.from_granite


@pytest.mark.parametrize("key", COMMITTED)
def test_a_committed_answer_carries_the_objects_own_verification_status(key):
    """
    'Oumuamua's published-figure validation belongs to 'Oumuamua. An answer
    file repeating it under another key would lend it to an object that has
    none, which is the one claim this project is most careful about.
    """
    assert answer_store.load(key).verification_status == \
        load(key).verification_status


def test_a_floor_answer_is_the_floor_verbatim():
    """
    A file frozen as the floor must be the floor, not prose that resembles it.
    The template is deterministic and takes no credential, so the committed
    bytes are reproducible here and compared directly.
    """
    from agent import template

    floors = [k for k in COMMITTED
              if answer_store.load(k).served_by == "deterministic_floor"]
    if not floors:
        pytest.skip("no answer is frozen as the floor")
    for key in floors:
        assert answer_store.load(key).text == template.explain(load(key).manifest), (
            f"{key} is labelled deterministic_floor but its text is not what "
            "agent/template.py produces for that manifest")
