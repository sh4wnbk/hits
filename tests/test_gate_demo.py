"""
tests/test_gate_demo.py — the live gate exhibit shows a real rejection.

A demonstration that a check works is worth nothing if the demonstration is
staged, and there are two ways to stage this one by accident. The fabricated
candidate could be rejected for some reason other than the injected digit,
which would show the gate working on a question nobody asked. Or the injected
token could be a string the manifest actually renders somewhere, which would
mean the exhibit rejects a figure the solver did emit and the endpoint is
lying in the direction that matters most.

So the assertions are specific: the injected token is not in the manifest's
rendering index, the fabricated text differs from the grounded text by exactly
that one substitution, and the gate's findings on it are exactly one finding
naming that token.
"""

import pytest

from app.gate_demo import _fabricate, _SWAP, gate_demo
from solver import objects
from solver.frozen import load, load_all


@pytest.fixture(scope="module")
def demos():
    return {fi.key: gate_demo(fi) for fi in load_all()}


def test_the_grounded_candidate_is_the_text_the_service_serves(demos):
    """
    Not a specimen written for the demo. What a reader watches pass the gate is
    the same string /explain returns, or the exhibit is about something else.
    """
    from agent.explain import explain
    for key, d in demos.items():
        served = explain(load(key).manifest, client=None)
        assert d["grounded"]["text"] == served.text
        assert d["grounded"]["verdict"]["grounded"] is True
        assert d["grounded"]["verdict"]["findings"] == []


def test_the_injected_token_is_a_number_the_solver_never_emitted(demos):
    """
    The claim the exhibit rests on. If the manifest rendered this string
    anywhere, the demo would be showing a true figure rejected.
    """
    for key, d in demos.items():
        m = load(key).manifest
        token = d["injection"]["injected_token"]
        assert token not in m.index(), (
            f"{key}: the injected {token!r} IS a rendering the manifest "
            "permits; the demo would be rejecting a real number")
        assert d["injection"]["solver_value"] in m.index()


def test_the_fabrication_is_one_substitution_and_nothing_else(demos):
    """
    The two candidates differ by one digit of one figure. A fabricated text
    that had drifted in any other way would let the gate reject it for a reason
    the exhibit does not name.
    """
    for key, d in demos.items():
        real = d["injection"]["solver_value"]
        fake = d["injection"]["injected_token"]
        grounded = d["grounded"]["text"]
        fabricated = d["fabricated"]["text"]

        assert len(real) == len(fake)
        differing = [(a, b) for a, b in zip(real, fake) if a != b]
        assert len(differing) == 1
        assert _SWAP[differing[0][0]] == differing[0][1]
        assert fabricated == grounded.replace(real, fake, 1)
        assert fabricated != grounded


def test_the_gate_rejects_exactly_the_injected_token(demos):
    """
    One finding, naming the injected string. More than one would mean the
    rejection is partly incidental; a different token would mean the exhibit's
    caption does not describe what happened.
    """
    for key, d in demos.items():
        verdict = d["fabricated"]["verdict"]
        assert verdict["grounded"] is False
        assert len(verdict["findings"]) == 1, verdict["findings"]
        finding = verdict["findings"][0]
        assert finding["text"] == d["injection"]["injected_token"]
        assert finding["reason"] == "fabricated-number"
        assert verdict["checks_run"]


def test_the_exhibit_is_stable_across_calls(demos):
    """
    A judge who reloads sees the same demonstration. A random injection would
    make two people looking at this endpoint unable to agree on what it showed.
    """
    for fi in load_all():
        again = gate_demo(fi)
        assert again == demos[fi.key]


def test_every_object_is_demonstrable(demos):
    """All three, so the exhibit is not a property of one lucky manifest."""
    assert set(demos) == set(objects.KEYS)
    for key, d in demos.items():
        assert d["object"] == key
        assert d["call_id"] == load(key).call_id


# ---------------------------------------------------------------------------
# The injector itself
# ---------------------------------------------------------------------------

def test_fabricate_refuses_to_return_a_permitted_string():
    """
    The guard that keeps the exhibit honest. Told that every single-digit
    variant is a real rendering, the injector returns None rather than
    presenting a true figure as an invention.
    """
    real = "393.34"
    every_variant = {real[:i] + _SWAP[c] + real[i + 1:]
                     for i, c in enumerate(real) if c.isdigit()}
    assert _fabricate(real, every_variant | {real}) is None
    assert _fabricate(real, {real}) is not None


def test_fabricate_changes_the_least_significant_digit_first():
    """
    A transposition in the last place is the one that survives a careless read,
    which makes it the one worth showing caught.
    """
    assert _fabricate("393.34", {"393.34"}) == "393.3" + _SWAP["4"]
