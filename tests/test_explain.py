"""
tests/test_explain.py — the generate-and-gate loop.

Driven entirely by stubs. Nothing here reaches watsonx, which is the point
twice over: the loop's behaviour is a property of the loop and not of a live
endpoint, and the no-credentials path is the one a user without an IBM account
gets, so it is exercised on every run rather than assumed.

The three-scenario proof of the invariant lives in tests/test_explain_proof.py.
This file is the mechanics: what the loop does with a rejection, what it puts in
the regeneration prompt, what it does when the endpoint is unreachable, and
where a credential is and is not allowed to come from.
"""

import os

import pytest

from agent import explain as agent_explain
from agent import granite, template
from solver.manifest import Manifest

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "manifests",
                       "validate_full.json")

# A reply whose every number is a manifest rendering, written by hand rather
# than taken from the template, so a test that says "Granite was served" is
# distinguishing a model's words from the floor's and not comparing the floor
# to itself.
GROUNDED_REPLY = (
    "HITS puts the Earth-relative departure C3 floor at 714.36 km^2/s^2, "
    "against a published 703 km^2/s^2, a difference of 11.36 km^2/s^2. The "
    "frame gate reproduces 26.28614 km/s. All figures are patched-conic, "
    "two-body.")

# 812.55 is on no ladder in the manifest. It is the shape the whole layer
# exists for: a plausible C3 floor, in the right unit and the right frame,
# that the solver never computed.
FABRICATED_REPLY = (
    "HITS puts the Earth-relative departure C3 floor at 812.55 km^2/s^2, "
    "against a published 703 km^2/s^2. All figures are patched-conic, "
    "two-body.")

FABRICATED_TOKEN = "812.55"


@pytest.fixture(scope="module")
def manifest():
    with open(FIXTURE, encoding="utf-8") as fh:
        return Manifest.from_json(fh.read())


class ScriptedGranite:
    """
    A stand-in for the watsonx client, returning scripted completions.

    Implements `generate(prompt) -> str` and nothing else, which is the whole
    surface agent/explain.py uses. It imports nothing from agent/granite.py, so
    a test passing here is evidence the loop does not depend on that module.
    """

    model_id = "stub/granite"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        # The last scripted reply repeats, so "fabricates on every call" is one
        # reply rather than a list whose length has to track the retry budget.
        index = min(len(self.prompts), len(self.replies))
        return self.replies[index - 1]

    @property
    def calls(self):
        return len(self.prompts)


class UnreachableGranite:
    model_id = "stub/granite"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        raise ConnectionError("watsonx did not answer")


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def test_grounded_first_pass_is_served_unchanged(manifest):
    client = ScriptedGranite(GROUNDED_REPLY)
    result = agent_explain.explain(manifest, client)

    assert result.served_by == agent_explain.GRANITE_FIRST_PASS
    assert result.text == GROUNDED_REPLY
    assert result.grounded
    assert result.regenerations == 0
    assert client.calls == 1


def test_a_fabricated_number_never_reaches_the_output(manifest):
    """
    The exit condition for this layer, stated as the thing that must not happen.

    The stub fabricates on every call, so the loop regenerates its full budget
    and then serves the floor. What is asserted is not merely that the floor was
    served: it is that 812.55 appears in no served text, having been generated
    three times.
    """
    client = ScriptedGranite(FABRICATED_REPLY)
    result = agent_explain.explain(manifest, client)

    assert FABRICATED_TOKEN not in result.text
    assert result.grounded
    assert result.served_by == agent_explain.DETERMINISTIC_FLOOR
    assert result.text == template.explain(manifest)
    assert client.calls == agent_explain.MAX_RETRIES + 1
    assert result.regenerations == agent_explain.MAX_RETRIES
    assert all(FABRICATED_TOKEN in a.text for a in result.attempts)


def test_the_rejected_token_is_fed_back_into_the_next_prompt(manifest):
    """
    Regeneration is re-prompting with the specific rejection, not just asking
    again. A retry that says only "try again" is a retry that has been given no
    reason to produce anything different.
    """
    client = ScriptedGranite(FABRICATED_REPLY)
    agent_explain.explain(manifest, client)

    first, second = client.prompts[0], client.prompts[1]
    assert FABRICATED_TOKEN not in first
    assert FABRICATED_TOKEN in second
    assert "fabricated-number" in second
    assert "REJECTED" in second
    assert "QUOTE-ONLY RULE" in second, "the rule is restated, not replaced"


def test_recovery_on_a_retry_is_credited_to_the_retry(manifest):
    client = ScriptedGranite(FABRICATED_REPLY, GROUNDED_REPLY)
    result = agent_explain.explain(manifest, client)

    assert result.served_by == agent_explain.GRANITE_AFTER_REGEN
    assert result.text == GROUNDED_REPLY
    assert result.regenerations == 1
    assert client.calls == 2


def test_an_unreachable_endpoint_degrades_the_explanation_only(manifest):
    """
    docs/ARCHITECTURE.md: every failure degrades the explanation, never the
    numbers. The retry budget is not spent on a transport error, because the
    budget exists to correct a fabrication given feedback about it and there is
    no feedback to give a connection error.
    """
    client = UnreachableGranite()
    result = agent_explain.explain(manifest, client)

    assert result.served_by == agent_explain.DETERMINISTIC_FLOOR
    assert result.grounded
    assert client.calls == 1
    assert "unreachable" in result.floor_reason
    assert result.attempts[0].error.startswith("ConnectionError")


def test_the_floor_is_gated_like_anything_else(manifest, monkeypatch):
    """
    The floor is served because it passed the gate, not because it is the floor.
    Break the template and the loop refuses to serve rather than emitting
    ungrounded prose.
    """
    monkeypatch.setattr(template, "explain",
                        lambda m: "The C3 floor is 999.99 km^2/s^2.")
    with pytest.raises(agent_explain.FloorUngrounded):
        agent_explain.explain(manifest, ScriptedGranite(FABRICATED_REPLY))


def test_served_by_values_are_separate_and_closed(manifest):
    values = set(agent_explain.SERVED_BY_VALUES)
    assert len(values) == 3, "the floor must never share a value with Granite"
    for client, expected in (
            (ScriptedGranite(GROUNDED_REPLY),
             agent_explain.GRANITE_FIRST_PASS),
            (ScriptedGranite(FABRICATED_REPLY, GROUNDED_REPLY),
             agent_explain.GRANITE_AFTER_REGEN),
            (ScriptedGranite(FABRICATED_REPLY),
             agent_explain.DETERMINISTIC_FLOOR)):
        assert agent_explain.explain(manifest, client).served_by == expected


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def test_no_credentials_means_the_floor_and_says_so(manifest, monkeypatch):
    for name in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL",
                 "WATSONX_MODEL_ID"):
        monkeypatch.delenv(name, raising=False)

    result = agent_explain.explain(manifest)

    assert result.served_by == agent_explain.DETERMINISTIC_FLOOR
    assert result.floor_reason == agent_explain.NO_CREDENTIALS
    assert result.grounded
    assert result.attempts == ()
    assert result.model_id == "", (
        "an offline result must not carry a model id it did not use")


def test_credentials_are_read_from_the_environment_only(monkeypatch):
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)
    monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)
    assert granite.from_env() is None
    assert not granite.credentials_present()

    monkeypatch.setenv("WATSONX_API_KEY", "not-a-real-key")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "not-a-real-project")
    client = granite.from_env()
    assert client is not None
    assert client.model_id == granite.DEFAULT_MODEL_ID

    monkeypatch.setenv("WATSONX_MODEL_ID", "ibm/some-other-granite")
    assert granite.from_env().model_id == "ibm/some-other-granite"


def test_no_credential_reaches_the_prompt(manifest, monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "sk-do-not-leak-me")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "project-do-not-leak-me")
    prompt = agent_explain.build_prompt(manifest)
    assert "do-not-leak-me" not in prompt


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

def test_the_prompt_carries_every_permitted_rendering(manifest):
    """
    A model told to quote only from a list has to be given the whole list. A
    rendering missing from the prompt is a correct sentence the gate will
    reject, which reads to a user as the system refusing its own numbers.
    """
    listing = agent_explain.permitted_numbers(manifest)
    for entry in manifest.entries:
        for rendering in entry.renderings:
            assert rendering in listing, f"{entry.id} rendering {rendering}"
        assert entry.kind in listing


def test_the_prompt_states_the_rules_the_gate_enforces(manifest):
    prompt = agent_explain.build_prompt(manifest)
    for required in ("QUOTE-ONLY RULE", "published", "frame", "unit",
                     "patched-conic", manifest.call_id):
        assert required in prompt


def test_the_question_reaches_the_prompt(manifest):
    prompt = agent_explain.build_prompt(manifest, question="Can we catch it?")
    assert "Can we catch it?" in prompt


# ---------------------------------------------------------------------------
# The wire shape
# ---------------------------------------------------------------------------
#
# The client is not exercised anywhere else in this suite, on purpose: the loop
# must be provably independent of it. But the failure that produced this
# section was a wire-shape failure, not a logic one. Granite returned
# incoherent token spam because /ml/v1/text/generation hands an instruct model
# a raw prompt with no chat template, and nothing in a test that stubs
# generate() could ever have seen it. So the request itself is asserted, with
# requests.post intercepted and no credential and no network involved.

class _CapturedPost:
    """Stands in for requests.post, recording the call and replying to script."""

    def __init__(self, status=200, payload=None, text=""):
        self.status, self.payload, self.text = status, payload or {}, text
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self

    # The bits of a requests.Response the client touches.
    @property
    def status_code(self):
        return 200 if self.calls[-1]["url"] == granite.IAM_URL else self.status

    def json(self):
        if self.calls[-1]["url"] == granite.IAM_URL:
            return {"access_token": "token-from-iam", "expires_in": 3600}
        return self.payload


CHAT_REPLY = {"choices": [{"message": {"role": "assistant",
                                       "content": "  a coherent sentence.  "}}]}


@pytest.fixture
def client():
    return granite.GraniteClient(api_key="sk-do-not-leak-me",
                                 project_id="project-1")


def test_the_client_posts_a_messages_array_to_the_chat_endpoint(client,
                                                               monkeypatch):
    post = _CapturedPost(payload=CHAT_REPLY)
    monkeypatch.setattr("requests.post", post)

    assert client.generate("PROMPT BODY") == "a coherent sentence."

    chat = post.calls[-1]
    assert chat["url"].endswith(granite.CHAT_PATH)
    assert "text/generation" not in chat["url"], (
        "an instruct model on the raw generation endpoint is the bug this "
        "endpoint choice exists to prevent")
    body = chat["json"]
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["messages"][1]["content"] == "PROMPT BODY"
    assert "input" not in body, "text/generation's field, not the chat one"
    assert body["model_id"] == granite.DEFAULT_MODEL_ID
    assert body["temperature"] == 0, "a sampled explanation makes served_by noise"


def test_the_default_model_is_the_one_confirmed_on_this_account():
    assert granite.DEFAULT_MODEL_ID == "ibm/granite-4-h-small"


def test_the_credential_travels_in_a_header_and_never_in_a_body(client,
                                                                monkeypatch):
    post = _CapturedPost(payload=CHAT_REPLY)
    monkeypatch.setattr("requests.post", post)
    client.generate("PROMPT BODY")

    iam, chat = post.calls[0], post.calls[1]
    assert iam["data"]["apikey"] == "sk-do-not-leak-me"
    assert "sk-do-not-leak-me" not in str(chat["json"])
    assert chat["headers"]["Authorization"] == "Bearer token-from-iam"


def test_a_refused_call_raises_rather_than_returning_prose(client, monkeypatch):
    """
    A 404 on a model id, which is how the previous default failed, has to reach
    the loop as an error so the attempt is recorded and the floor is served.
    Returning an error body as text would put watsonx's prose into a response
    labelled as an explanation.
    """
    monkeypatch.setattr("requests.post",
                        _CapturedPost(status=404, payload={},
                                      text="model_not_supported"))
    with pytest.raises(granite.GraniteError, match="404"):
        client.generate("PROMPT BODY")


def test_an_empty_completion_is_an_error_not_an_explanation(client, monkeypatch):
    monkeypatch.setattr(
        "requests.post",
        _CapturedPost(payload={"choices": [{"message": {"content": "   "}}]}))
    with pytest.raises(granite.GraniteError, match="empty"):
        client.generate("PROMPT BODY")
