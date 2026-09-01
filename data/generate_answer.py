"""
data/generate_answer.py — one watched Granite generation, frozen if it grounds.

Run by a person, at a terminal, one object at a time. Not by CI, not by the web
process, and not by the test suite. This is the only script in the repository
that spends watsonx quota, and it is separate from everything else so that
spending it is always a deliberate act.

## Why absent credentials are an error here

Everywhere else in HITS, no credential is an ordinary outcome: agent/explain.py
serves the deterministic floor and reports why, because a reader without an IBM
account is a reader the tool still has to work for. That is the accessibility
gate and it stays.

Here it is inverted. The entire purpose of this script is to make a live call
and record what came back, so falling quietly to the floor would produce a file
labelled as a watched generation containing template prose. Rather than write
that file, the script exits nonzero and says the credentials are missing.

## Why a floored run writes nothing

A floor is a correct answer and a perfectly good thing to serve; what it is not
is a Granite answer. If it were written out, the file would sit in
data/answers/ looking exactly like a successful generation, and the next person
to run `git add` would commit it. CLAUDE.md is explicit that an offline result
must never be mis-credited to the credentialed system, so the failure leaves no
artefact at all and prints the rejected tokens instead.

## What is printed and what is not

Everything a reader needs to judge the run: which path served it, whether the
gate passed it, which model answered, what Guardian said, and the full text.
Never the credential. `granite.from_env()` reads the environment inside the
client and no value is echoed, logged, or written here.

## Usage

    source .venv/bin/activate
    export WATSONX_API_KEY=...          # in your own shell, not in a file
    export WATSONX_PROJECT_ID=...
    python data/generate_answer.py borisov

Exit status is 0 only if a Granite answer passed the gate and was written.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import granite
from agent.explain import explain
from app.answers import CachedAnswer, save
from solver import objects
from solver.frozen import load

RULE = "-" * 72

# The question turn, which is where the target's identity enters.
#
# A prompt that never named the object left Granite to infer what it was, and
# on 2I/Borisov it inferred "a target planet": a grounded answer, every figure
# from the manifest, describing the wrong kind of body. The designation is not
# a number and is not in the manifest's permitted numbers, so naming it here
# costs the gate nothing. It is stated per object rather than as a standing
# rule because the standing rules are the same on every call and this is the
# one thing that is not.
QUESTION = ("Explain this computed intercept of {designation}, an interstellar "
            "object and not a planet, in plain language to someone with no "
            "mission-design training.")


def _fail(message: str) -> int:
    print(f"\nFAILED: {message}")
    return 1


def generate(key: str) -> int:
    try:
        objects.get(key)
    except KeyError as exc:
        return _fail(str(exc))

    frozen = load(key)

    client = granite.from_env()
    if client is None:
        return _fail(
            "no watsonx creds in env. Set WATSONX_API_KEY and "
            "WATSONX_PROJECT_ID in this shell and run again. This script makes "
            "a live call on purpose and will not fall back to the floor.")

    print(RULE)
    print(f"object          {key} ({frozen.designation})")
    print(f"call_id         {frozen.call_id}")
    print(f"manifest        data/manifests/{key}.json, "
          f"{len(frozen.manifest.entries)} entries")
    print(f"model           {client.model_id}")
    print(RULE)
    print("calling Granite once. The gate may regenerate internally up to twice.")
    print(RULE)

    question = QUESTION.format(designation=frozen.designation)
    print(f"question        {question}")
    print(RULE)

    e = explain(frozen.manifest, client=client, question=question)

    print(f"served_by       {e.served_by}")
    print(f"grounded        {e.grounded}")
    print(f"model_id        {e.model_id!r}")
    print(f"guardian        {e.verdict.advisory}")
    print(f"regenerations   {e.regenerations}")
    print(f"floor_reason    {e.floor_reason!r}")
    print(f"attempts        {len(e.attempts)}")
    print(RULE)
    print(e.text)
    print(RULE)

    # Every attempt the gate refused, with the tokens it refused them for, and
    # the prose those tokens sat in. This is the diagnostic that matters on a
    # floored run and it is printed on a successful one too, because a pass on
    # the second attempt is worth seeing.
    #
    # The text is printed and not just the tokens because the tokens alone do
    # not say what went wrong. A run that floored on a bare `13` and a
    # `wrong-unit` on `km` was diagnosable only by reconstructing candidate
    # spellings offline afterwards and matching their findings; the prose would
    # have said it outright. A rejected attempt is the only record of what the
    # model actually wrote, and it is discarded when this process exits.
    for a in e.attempts:
        if a.error:
            print(f"attempt {a.index}: transport error: {a.error}")
        elif a.findings:
            print(f"attempt {a.index}: rejected on "
                  f"{[(f.text, f.reason) for f in a.findings]}")
            print(f"attempt {a.index} text:")
            print(a.text)
            print()
        else:
            print(f"attempt {a.index}: grounded")
    print(RULE)

    if e.served_by == "deterministic_floor":
        return _fail(
            f"{key} fell to the deterministic floor, so nothing was written. "
            f"floor_reason: {e.floor_reason!r}. The floor is a correct answer "
            "but it is not a Granite answer, and a file here would be "
            "indistinguishable from a successful generation once committed.")

    if not e.grounded:
        return _fail(
            f"{key} was served as {e.served_by} but the verdict is not "
            "grounded. Nothing written. This should be unreachable: explain() "
            "only returns a grounded verdict, so reaching it means the "
            "invariant in agent/explain.py has broken.")

    answer = CachedAnswer(
        object_key=key,
        text=e.text,
        served_by=e.served_by,
        model_id=e.model_id,
        generated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        call_id=frozen.call_id,
        verification_status=frozen.verification_status,
        regenerations=e.regenerations,
        verified_grounded=True,
        advisory=e.verdict.advisory,
    )
    path = save(answer)
    print(f"WROTE {path}")
    print(f"      served_by {answer.served_by}, generated_at {answer.generated_at}")
    return 0


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print(f"\nusage: python data/generate_answer.py <object_key>")
        print(f"       object_key is one of {list(objects.KEYS)}")
        return 2
    return generate(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
