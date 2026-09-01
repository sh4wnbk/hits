"""
agent/explain.py — generate, gate, regenerate, and fall to the floor.

The fallible path, built on top of a floor that was proven first. The order
matters and it is the same discipline the gate itself was built under: the
thing that catches the failure exists and is watched working before the thing
that fails is wired in.

## The invariant

The system never serves an ungrounded explanation. There is one exit from this
module and everything leaves through it holding a grounded verdict:

  1. Granite generates. verify.groundedness.check runs. If it is grounded, it
     is served as `granite_first_pass`.
  2. If not, regenerate, with the rejected tokens and the quote-only rule fed
     back in. Capped at MAX_RETRIES, which is small on purpose: a model that
     fabricates a number once tends to fabricate it again, and a long retry
     budget mostly buys latency. If a retry comes back grounded it is served as
     `granite_after_regen`.
  3. After the retries are spent, the deterministic floor is served as
     `deterministic_floor`.

`served_by` carries which of those three happened, in separate values, because
CLAUDE.md requires that an offline or fallback result is never mis-credited to
the credentialed system. A judges page reading only the text could not tell a
Granite answer from the template; reading `served_by` it cannot fail to.

## Credentials

They come from the environment, through agent/granite.py, and nowhere else.
Absent credentials are not an error: the path is `deterministic_floor`, and the
whole loop is exercised in tests by a stub that never touches watsonx. The
no-key path is the one a user without an account gets, so it is the one that
must not be an afterthought.

## What a transport failure does

It is recorded and the floor is served, without consuming the retry budget on
further calls. The budget exists to correct a fabrication given specific
feedback about it, and there is no feedback to give a connection error. This is
the degrade path in docs/ARCHITECTURE.md: the explanation degrades, the numbers
do not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

from agent import granite, template
from verify.groundedness import Finding, Verdict, check

# The three ways a response can have been produced. Separate values, never
# collapsed into a boolean: "was a model involved" is not the question a reader
# of a validation surface is asking.
GRANITE_FIRST_PASS = "granite_first_pass"
GRANITE_AFTER_REGEN = "granite_after_regen"
DETERMINISTIC_FLOOR = "deterministic_floor"

SERVED_BY_VALUES = (GRANITE_FIRST_PASS, GRANITE_AFTER_REGEN, DETERMINISTIC_FLOOR)

# Regenerations after the first pass. Small deliberately: a model that
# fabricates a number once tends to repeat it, so the third and fourth attempt
# mostly buy latency, and the floor is already a correct answer.
MAX_RETRIES = 2

NO_CREDENTIALS = "no watsonx credentials in the environment"
RETRIES_EXHAUSTED = "every Granite attempt quoted a number the manifest does not render"


class FloorUngrounded(RuntimeError):
    """
    The deterministic floor failed its own gate.

    Raised rather than served, because at this point there is nothing left that
    is safe to return, and returning ungrounded prose is the single failure
    this whole layer exists to prevent. It can only happen if the template and
    the manifest have drifted apart, which tests/test_template.py exists to
    catch at build time.
    """


@dataclass(frozen=True)
class Attempt:
    """One generation, and what the gate made of it."""
    index: int
    text: str
    findings: Tuple[Finding, ...] = ()
    error: str = ""

    @property
    def grounded(self) -> bool:
        return not self.findings and not self.error


@dataclass(frozen=True)
class Explanation:
    """
    What the loop serves, and the record of how it got there.

    `verdict` is the gate's verdict on `text` and is always grounded. The
    attempts are kept, rejected ones included, because a response that says it
    fell to the floor should be able to show what it rejected on the way.
    """
    text: str
    served_by: str
    verdict: Verdict
    attempts: Tuple[Attempt, ...] = ()
    floor_reason: str = ""
    model_id: str = ""

    @property
    def regenerations(self) -> int:
        """Generation calls made after the first pass."""
        return len(self.attempts[1:])

    @property
    def grounded(self) -> bool:
        return self.verdict.grounded


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

SYSTEM_FRAMING = """\
You explain the output of a deterministic orbital-mechanics solver to a general
reader. The solver has already run and finished. You interpret its output; you
do not produce figures of your own.

Open with a single plain-language sentence a non-scientist can read, saying what
the result means. Then give the detail underneath it. Do not open with a list,
a heading, or a restatement of the request.

Refer to the target by the name the question gives it, and do not assume it is
a planet.

Do not say whether the mission could or could not be flown, and do not say a
probe could reach the target. This system computes what a transfer costs and
models no launch vehicle, so the cost is the input to that judgement and not
the judgement. Report the cost and stop there."""

QUOTE_ONLY_RULE = """\
QUOTE-ONLY RULE. Write no number that does not appear verbatim in the list of
permitted numbers above. Not a rounding of one, not a total of two of them, not
a number you are confident is correct. A number this solver did not emit is
rejected whether it happens to be right or not, so if a quantity you want is
not on the list, say it in words or leave it out.

Write units exactly as they are shown. A correct value with the wrong unit is a
different claim and is rejected.

If you name a frame (heliocentric, Earth-relative, target-relative), name the
one listed for that number.

Numbers marked `published` are the source paper's, not this system's. Introduce
them as published, or with "against" or "versus". Numbers marked `computed` or
`derived` are this system's own: never describe one as published or as a
benchmark figure.

Do not cite a figure, equation, table or page number. Reference numbers are
checked against the source citations and a wrong one is treated as a fabricated
number wearing a label.

Write a date in one of the forms the list gives for it. Each date is listed
twice, as "2027-06-21" and as "June 21, 2027", and either is accepted exactly as
shown. A third spelling is not: "21 June 2027" and "Jun 21, 2027" are rejected
like any other string that is not on the list.

Do not say which of two values is larger, and do not say whether a check
passed, failed, or exceeded its tolerance. You were given numbers, not their
ordering, and working out the ordering is arithmetic you are not doing here.
Say what each value is and what the difference between them is, both of which
are on the list, and stop there.

Write connected prose. State that the model is patched-conic and two-body, with
no n-body integration and no non-gravitational forces."""


# The manifest's placeholder for an entry that has no frame, which is a value
# in the schema's closed lexicon and not a word. It must never reach the model:
# handed "frame n_a", Granite wrote "the flight time is 365 days, or 1 year, in
# the n_a frame" and served it to a reader, and the gate had no reason to
# object because n_a is not a number. Whatever the prompt shows, the model will
# eventually say.
NO_FRAME = "n_a"


def permitted_numbers(manifest) -> str:
    """
    Every number the explanation is allowed to write, with what it is.

    The kind, unit and frame travel with each line because they are what the
    gate checks besides the digits, and a model that is not told them cannot
    satisfy them.

    The frame clause is omitted entirely for an entry that has none. Writing
    "frame n_a" leaked an internal token into user-facing prose; writing
    "no frame" would invite "in no frame", which is not English either. A
    dimensionless quantity is better served by the prompt saying nothing about
    its frame, since there is nothing to say.
    """
    lines = []
    for entry in manifest.entries:
        alternates = entry.renderings[1:]
        facts = [entry.kind, f"unit {entry.unit}"]
        if entry.frame != NO_FRAME:
            facts.append(f"frame {entry.frame}")
        line = f"- {entry.canonical}  [{', '.join(facts)}]  {entry.label}"
        if alternates:
            line = f"{line}  (may also be written {', '.join(alternates)})"
        lines.append(line)
    return "\n".join(lines)


def _rejection_block(rejected: Sequence[Finding], previous: str) -> str:
    named = "\n".join(
        f'  - "{f.text}"  ({f.reason}): {f.note}' for f in rejected)
    return (
        "YOUR PREVIOUS ANSWER WAS REJECTED by the groundedness gate.\n\n"
        "It said:\n"
        f"{previous}\n\n"
        "These are what it was rejected for:\n"
        f"{named}\n\n"
        "Rewrite it. Replace every token above with a number from the "
        "permitted list, or drop the sentence that carried it. The quote-only "
        "rule still applies in full.")


# The standing instructions, which are the same for every call this layer ever
# makes. They belong in the system turn because that is where an instruct model
# expects the rules it is being held to, and because a rule repeated in the
# user turn competes for attention with the material that actually differs
# between calls. What differs between calls is the question, the manifest and,
# on a retry, the rejection: that is the user turn and nothing else.
SYSTEM_RULES = "\n\n".join([SYSTEM_FRAMING, QUOTE_ONLY_RULE])


def _default_question(manifest) -> str:
    """
    The question asked when a caller does not supply one, naming the target.

    A prompt that never says what the target is leaves the model to guess, and
    Granite guessed "a target planet" for 2I/Borisov on a run that was
    otherwise grounded. The designation is in the manifest header the solver
    emitted, so a caller who asks nothing still gets a prompt that knows what
    it is describing.

    This is identity, not a quantity. It travels in the question turn and never
    in the permitted numbers, and the gate is untouched by it: the tokenizer
    already treats a digit fused to a letter as an identifier, so "2I" is not a
    number an explanation could be accused of quoting.
    """
    designation = ""
    inputs = getattr(manifest, "inputs", None)
    if isinstance(inputs, dict):
        designation = str(inputs.get("designation", "") or "")
    if not designation:
        return ("Explain this result in plain language to someone with no "
                "mission-design training.")
    return (f"Explain this computed intercept of {designation}, an "
            "interstellar object and not a planet, in plain language to "
            "someone with no mission-design training.")


def build_prompt(manifest, question: str = "",
                 rejected: Sequence[Finding] = (),
                 previous: str = "") -> str:
    """
    The user turn for one attempt: the material specific to this call.

    The rules are not here. They are in SYSTEM_RULES and travel in the system
    turn. Regeneration differs from a first attempt only by the feedback block.
    """
    asked = question or _default_question(manifest)
    parts = [
        f"THE QUESTION: {asked}",
        f"SOLVER CALL: {manifest.producer}, call_id {manifest.call_id}",
        f"FIDELITY: {manifest.fidelity_note}",
        f"PERMITTED NUMBERS:\n{permitted_numbers(manifest)}",
    ]
    if rejected:
        parts.append(_rejection_block(rejected, previous))
    # An instruction, not a completion stub. "EXPLANATION:" is the shape a raw
    # text-generation prompt ends in, and this goes to a chat endpoint as a
    # user turn, where a trailing label reads as something to echo.
    parts.append("Write the explanation now, and write nothing else.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def _serve_floor(floor_text: str, manifest, attempts: Tuple[Attempt, ...],
                 reason: str, model_id: str) -> Explanation:
    """
    Serve the deterministic template, having gated it like anything else.

    The floor is not trusted because it is the floor. It goes through the same
    check every Granite candidate goes through, so the invariant is enforced at
    the point of serving rather than assumed at the point of writing.
    """
    verdict = check(floor_text, manifest)
    if not verdict.grounded:
        raise FloorUngrounded(
            "the deterministic template failed its own gate, so there is "
            "nothing safe left to serve: "
            + "; ".join(f"{f.reason} {f.text!r}" for f in verdict.findings))
    return Explanation(text=floor_text, served_by=DETERMINISTIC_FLOOR,
                       verdict=verdict, attempts=attempts,
                       floor_reason=reason, model_id=model_id)


def explain(manifest, client=None, *, question: str = "",
            max_retries: int = MAX_RETRIES) -> Explanation:
    """
    Explain one solver call, and never return an ungrounded explanation.

    `client` is any object with `generate(prompt, system=...) -> str`. Left
    None, the
    environment decides: credentials present means Granite, credentials absent
    means the floor. Nothing about a credential ever reaches this function's
    arguments.
    """
    # Built before the fallible path runs, not after it fails. A fallback
    # constructed only on the failure branch is a fallback nobody has watched.
    floor_text = template.explain(manifest)

    if client is None:
        client = granite.from_env()
    if client is None:
        return _serve_floor(floor_text, manifest, (), NO_CREDENTIALS, "")

    model_id = getattr(client, "model_id", "")
    attempts: list = []
    prompt = build_prompt(manifest, question=question)

    for index in range(max_retries + 1):
        try:
            candidate = client.generate(prompt, system=SYSTEM_RULES)
        except Exception as exc:                      # noqa: BLE001
            attempts.append(Attempt(index=index, text="",
                                    error=f"{type(exc).__name__}: {exc}"))
            return _serve_floor(floor_text, manifest, tuple(attempts),
                                f"Granite was unreachable: {exc}", model_id)

        verdict = check(candidate, manifest)
        if verdict.grounded:
            attempts.append(Attempt(index=index, text=candidate))
            served = GRANITE_FIRST_PASS if index == 0 else GRANITE_AFTER_REGEN
            return Explanation(text=candidate, served_by=served,
                               verdict=verdict, attempts=tuple(attempts),
                               model_id=model_id)

        attempts.append(Attempt(index=index, text=candidate,
                                findings=tuple(verdict.findings)))
        prompt = build_prompt(manifest, question=question,
                              rejected=verdict.findings, previous=candidate)

    return _serve_floor(floor_text, manifest, tuple(attempts),
                        RETRIES_EXHAUSTED, model_id)
