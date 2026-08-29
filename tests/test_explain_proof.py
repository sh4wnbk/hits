"""
tests/test_explain_proof.py — the invariant, demonstrated rather than argued.

CLAUDE.md: no behaviour is believed until a test or a plot demonstrates it, and
an explanation of what the code does is a hypothesis until executed. The
hypothesis under test here is the one claim the whole interpretation layer
rests on:

    the system never serves an ungrounded explanation.

Three scenarios, covering the three ways a response can be produced, and the
invariant asserted across all of them. This file adds no feature. It exists so
that a reader who trusts nothing else in agent/ can watch a fabricated number
be generated, be caught, be regenerated against, and never appear in anything
served.

The failing case is first, because it is the one that matters. A layer that
only demonstrates its success path has demonstrated nothing.
"""

import pytest

from agent import explain as agent_explain
from agent import template
from tests.test_explain import (
    FIXTURE, GROUNDED_REPLY, ScriptedGranite,
)
from solver.manifest import Manifest
from verify.groundedness import check

# Three plausible C3 floors, in the right unit and the right frame, that the
# solver never computed. None is a rendering on any ladder in the manifest.
# They differ between calls on purpose: a stub that repeats one number could be
# caught by a loop that merely remembers what it rejected last time, and the
# claim being made is stronger than that.
FABRICATIONS = ("812.55", "690.12", "1502.7")


def _fabricating_reply(value: str) -> str:
    return (
        f"HITS puts the Earth-relative departure C3 floor at {value} "
        "km^2/s^2, against a published 703 km^2/s^2. All figures are "
        "patched-conic, two-body.")


FABRICATED_REPLIES = tuple(_fabricating_reply(v) for v in FABRICATIONS)


@pytest.fixture(scope="module")
def manifest():
    with open(FIXTURE, encoding="utf-8") as fh:
        return Manifest.from_json(fh.read())


def _assert_invariant(result, manifest):
    """
    What must hold of every response, whichever path produced it.

    Re-gated here rather than trusting the verdict the loop attached, so the
    assertion is about the text that was served and not about a field next to
    it.
    """
    assert result.served_by in agent_explain.SERVED_BY_VALUES
    assert check(result.text, manifest).grounded, (
        f"{result.served_by} served ungrounded prose")
    for fabricated in FABRICATIONS:
        assert fabricated not in result.text, (
            f"{fabricated} was generated and reached the output")


# ---------------------------------------------------------------------------
# Scenario 1: fabricates on every call
# ---------------------------------------------------------------------------

def test_fabricating_on_every_call_falls_to_the_floor(manifest):
    """
    A model that will not stop inventing numbers, driven to the end of the
    retry budget.

    Every assertion in this test is a link in the chain: the retries were
    actually attempted, every attempt was actually rejected, the floor was
    actually served, and no invented number survived to the output.
    """
    client = ScriptedGranite(*FABRICATED_REPLIES)
    result = agent_explain.explain(manifest, client)

    assert client.calls == agent_explain.MAX_RETRIES + 1
    assert result.regenerations == agent_explain.MAX_RETRIES

    assert len(result.attempts) == agent_explain.MAX_RETRIES + 1
    for attempt, fabricated in zip(result.attempts, FABRICATIONS):
        assert not attempt.grounded
        assert fabricated in attempt.text
        assert any(f.text == fabricated and f.reason == "fabricated-number"
                   for f in attempt.findings)

    assert result.served_by == agent_explain.DETERMINISTIC_FLOOR
    assert result.floor_reason == agent_explain.RETRIES_EXHAUSTED
    assert result.text == template.explain(manifest)
    _assert_invariant(result, manifest)


def test_each_regeneration_was_told_what_it_got_wrong(manifest):
    """
    The regenerations are re-prompts carrying the specific rejection, which is
    what makes them regenerations and not repetitions.
    """
    client = ScriptedGranite(*FABRICATED_REPLIES)
    agent_explain.explain(manifest, client)

    assert len(client.prompts) == agent_explain.MAX_RETRIES + 1
    for index, prompt in enumerate(client.prompts[1:]):
        assert FABRICATIONS[index] in prompt, (
            "the retry was not told which token was rejected")
        assert "fabricated-number" in prompt


# ---------------------------------------------------------------------------
# Scenario 2: grounded on the first try
# ---------------------------------------------------------------------------

def test_grounded_on_the_first_try_is_served_as_granite(manifest):
    client = ScriptedGranite(GROUNDED_REPLY)
    result = agent_explain.explain(manifest, client)

    assert result.served_by == agent_explain.GRANITE_FIRST_PASS
    assert result.regenerations == 0
    assert client.calls == 1
    assert result.text == GROUNDED_REPLY
    assert result.text != template.explain(manifest), (
        "a Granite pass must be distinguishable from the floor, or served_by "
        "is decoration")
    _assert_invariant(result, manifest)


# ---------------------------------------------------------------------------
# Scenario 3: grounded only on the second regeneration
# ---------------------------------------------------------------------------

def test_grounded_on_the_last_retry_is_credited_to_the_retry(manifest):
    """
    Recovery at the far edge of the budget. served_by must say
    granite_after_regen: the answer is Granite's, and it took two corrections
    to get there, and both halves of that are things a judges page has to be
    able to state.
    """
    client = ScriptedGranite(FABRICATED_REPLIES[0], FABRICATED_REPLIES[1],
                             GROUNDED_REPLY)
    result = agent_explain.explain(manifest, client)

    assert result.served_by == agent_explain.GRANITE_AFTER_REGEN
    assert result.regenerations == agent_explain.MAX_RETRIES
    assert client.calls == agent_explain.MAX_RETRIES + 1
    assert result.text == GROUNDED_REPLY
    assert [a.grounded for a in result.attempts] == [False, False, True]
    _assert_invariant(result, manifest)


# ---------------------------------------------------------------------------
# The invariant, across every path at once
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("replies,expected", [
    ((GROUNDED_REPLY,), agent_explain.GRANITE_FIRST_PASS),
    ((FABRICATED_REPLIES[0], GROUNDED_REPLY), agent_explain.GRANITE_AFTER_REGEN),
    (FABRICATED_REPLIES[:2] + (GROUNDED_REPLY,),
     agent_explain.GRANITE_AFTER_REGEN),
    (FABRICATED_REPLIES, agent_explain.DETERMINISTIC_FLOOR),
])
def test_no_ungrounded_explanation_is_ever_served(manifest, replies, expected):
    result = agent_explain.explain(manifest, ScriptedGranite(*replies))
    assert result.served_by == expected
    _assert_invariant(result, manifest)


def test_the_offline_path_holds_the_invariant_too(manifest, monkeypatch):
    """
    The path with no IBM account at all. It is not a degraded corner of the
    system: CLAUDE.md makes working with no API key a design gate, so it is
    held to the same invariant as the credentialed path.
    """
    for name in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID"):
        monkeypatch.delenv(name, raising=False)
    result = agent_explain.explain(manifest)
    assert result.served_by == agent_explain.DETERMINISTIC_FLOOR
    assert result.floor_reason == agent_explain.NO_CREDENTIALS
    _assert_invariant(result, manifest)
