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
        self.systems = []

    def generate(self, prompt, system=""):
        self.prompts.append(prompt)
        self.systems.append(system)
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

    def generate(self, prompt, system=""):
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
    # The quote-only rule is not restated in the retry's user turn any more; it
    # rides the system turn on every call, so it is in force on the retry
    # without competing with the feedback for attention. Both are asserted,
    # because "the rule still applies" is the claim and where it lives is the
    # implementation of it.
    assert "quote-only rule still applies" in second
    assert client.systems[1] == agent_explain.SYSTEM_RULES
    assert "QUOTE-ONLY RULE" in client.systems[1]


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


def test_the_rules_the_gate_enforces_are_in_the_system_turn(manifest):
    """
    The standing rules belong in the system turn and the per-call material in
    the user turn. A rule repeated in the user turn competes for attention with
    the thing that actually differs between calls.
    """
    for required in ("QUOTE-ONLY RULE", "published", "frame", "unit",
                     "patched-conic", "plain-language sentence"):
        assert required in agent_explain.SYSTEM_RULES


def test_the_user_turn_carries_only_the_call(manifest):
    prompt = agent_explain.build_prompt(manifest)
    assert manifest.call_id in prompt
    assert "PERMITTED NUMBERS" in prompt
    assert "QUOTE-ONLY RULE" not in prompt, (
        "the standing rules moved to the system turn; a copy here is the "
        "duplication the split exists to remove")


def test_the_system_rules_reach_the_client(manifest):
    """
    Threaded, not merely defined. A system message the loop never passes is a
    system message the model never sees.
    """
    client = ScriptedGranite(GROUNDED_REPLY)
    agent_explain.explain(manifest, client)
    assert client.systems == [agent_explain.SYSTEM_RULES]


def test_no_prompt_the_model_sees_contains_the_no_frame_placeholder(manifest):
    """
    `n_a` is the manifest schema's placeholder for an entry with no frame. It
    is a lexicon value, not a word, and handed "frame n_a" Granite wrote "in
    the n_a frame" into prose shown to a reader. Whatever the prompt contains,
    the model will eventually say, so the placeholder must not be in it.

    Checked on the system turn, the first user turn, and a regeneration user
    turn carrying a rejection block, because the rejection block quotes the
    gate's own findings and those are built from manifest fields too.
    """
    from verify.groundedness import Finding

    dimensionless = [e for e in manifest.entries
                     if e.frame == agent_explain.NO_FRAME]
    assert dimensionless, (
        "this manifest has no frameless entry, so it cannot prove the leak is "
        "closed")

    rejected = (Finding(text="99999", reason="fabricated-number", start=0,
                        note="99999 is not a manifest rendering"),)
    surfaces = {
        "system": agent_explain.SYSTEM_RULES,
        "user": agent_explain.build_prompt(manifest),
        "user on regen": agent_explain.build_prompt(
            manifest, rejected=rejected, previous="a rejected answer"),
    }
    for name, text in surfaces.items():
        assert agent_explain.NO_FRAME not in text, (
            f"the {name} turn hands the model {agent_explain.NO_FRAME!r}")


def test_the_question_reaches_the_prompt(manifest):
    prompt = agent_explain.build_prompt(manifest, question="Can we catch it?")
    assert "Can we catch it?" in prompt


def test_the_prompt_says_what_the_target_is():
    """
    The bug this closes: with nothing in the prompt saying what the object was,
    Granite called 2I/Borisov "a target planet" on a run that was otherwise
    grounded. Every figure came from the manifest and the body was the wrong
    kind of body, which is exactly the class of error the gate cannot catch,
    because it checks numbers and this is a noun.

    The designation is in the manifest header the solver emitted, so a caller
    who asks no question still gets a prompt that knows its subject.
    """
    from solver.frozen import load

    for key in ("oumuamua", "borisov", "atlas"):
        m = load(key).manifest
        designation = m.inputs["designation"]
        prompt = agent_explain.build_prompt(m)
        assert designation in prompt, key
        assert "interstellar object" in prompt
        assert "not a planet" in prompt

    assert "do not assume it is\na planet" in agent_explain.SYSTEM_RULES


def test_a_manifest_with_no_designation_still_gets_a_question(manifest):
    """
    A validate manifest is a summary of five comparisons, not a transfer to an
    object, and its header carries no designation. The default question falls
    back rather than naming an empty string, so the shape that has no target is
    not handed a sentence claiming it has one.
    """
    assert "designation" not in manifest.inputs
    prompt = agent_explain.build_prompt(manifest)
    assert "THE QUESTION:" in prompt
    assert "interstellar object" not in prompt
    assert "None" not in prompt.splitlines()[0]


def test_the_targets_identity_is_not_a_permitted_number():
    """
    Identity enters through the question turn and nowhere else. If a
    designation ever appeared among the permitted numbers, the gate would be
    accepting "2I" as a quotable figure, which is the one fix that was off the
    table: it would let a bare 2 through wherever the tokenizer split it.
    """
    from solver.frozen import load

    for key in ("oumuamua", "borisov", "atlas"):
        m = load(key).manifest
        permitted = agent_explain.permitted_numbers(m)
        assert m.inputs["designation"] not in permitted
        for fragment in ("1I", "2I", "3I", "Borisov", "Oumuamua", "ATLAS",
                         "planet", "interstellar"):
            assert fragment not in permitted, (key, fragment)


def test_a_designation_is_never_a_number_the_gate_can_be_asked_about(manifest):
    """
    The check that made this fix safe to ship without touching verify/.

    Naming the object in the prompt is only free if the name cannot be mistaken
    for a quoted figure. It cannot: the tokenizer refuses a digit fused to a
    word character, which is what already keeps C3, J2000 and v_inf2 out, and
    a designation is the same shape. Asserted here as well as in
    tests/test_extract.py because that test reads a corpus case and this one
    states the rule for all three objects, including the slash form no corpus
    case contains.
    """
    from verify.extract import extract
    from verify.groundedness import check

    for designation in ("1I/'Oumuamua", "2I/Borisov", "3I/ATLAS"):
        text = (f"The probe reaches {designation}, an interstellar object and "
                "not a planet, and the flight time is 20 years.")
        tokens = [t.text for t in extract(text)]
        assert tokens == ["20"], (designation, tokens)
        for stray in ("1", "2", "3"):
            assert stray not in tokens


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
