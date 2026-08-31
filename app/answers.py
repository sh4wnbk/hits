"""
app/answers.py — the committed Granite answers, and how they are served.

## Why an answer is cached rather than generated per request

Three reasons, and only the first is about money.

A live call costs watsonx quota on every page load, and a judge reloading the
page would spend it. A live call also takes seconds, which on a free instance
that may itself be cold-starting is the difference between a working demo and a
blank panel. And a live call is not reproducible: the same manifest can return
`granite_first_pass` on one attempt and `deterministic_floor` on the next,
which CLAUDE.md records happening on this exact prompt shape.

So the generation is watched once, by a person, and what was watched is what is
served. The cache is the record of a specific generation, not a summary of one:
it carries `served_by`, `model_id` and `generated_at` verbatim, so a reader is
told which path produced the prose and when, and can tell a Granite answer from
the floor without taking anyone's word for it.

## Why the cache is still gated on read

`load()` does not re-check grounding, and `verified_grounded` is recorded at
freeze time rather than recomputed. But tests/test_answers.py runs the gate over
every committed answer against that object's committed manifest, so a cached
answer that stopped being grounded, because the manifest changed under it, fails
CI rather than reaching a reader. The check is at build time because the
alternative, running it per request, would make the page's latency depend on
the gate and would still not catch anything CI does not.

## The live path

`?live=1` bypasses all of this and calls Granite. It is the judges-page
regenerate button: someone who does not believe the cache came from a model can
make the call themselves and watch what comes back, including watching it fall
to the floor. That path is opt-in precisely because it can fail, and a failure
there is honest rather than hidden: an exhausted quota returns
`deterministic_floor` with the transport reason attached.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

ANSWER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "answers")


@dataclass(frozen=True)
class CachedAnswer:
    """
    One watched generation, frozen.

    `served_by` is carried rather than assumed. A cache file exists only because
    a person watched a Granite call succeed, so the value should always be
    `granite_first_pass` or `granite_after_regen`; it is stored anyway, because
    a field that is asserted in a docstring and absent from the data is a claim
    nobody can check.
    """
    object_key: str
    text: str
    served_by: str
    model_id: str
    generated_at: str
    call_id: str
    verification_status: str
    regenerations: int = 0
    verified_grounded: bool = False
    advisory: str = "unavailable"

    @property
    def from_granite(self) -> bool:
        return self.served_by in ("granite_first_pass", "granite_after_regen")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_key": self.object_key,
            "text": self.text,
            "served_by": self.served_by,
            "model_id": self.model_id,
            "generated_at": self.generated_at,
            "call_id": self.call_id,
            "verification_status": self.verification_status,
            "regenerations": self.regenerations,
            "verified_grounded": self.verified_grounded,
            "advisory": self.advisory,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CachedAnswer":
        return cls(
            object_key=d["object_key"],
            text=d["text"],
            served_by=d["served_by"],
            model_id=d["model_id"],
            generated_at=d["generated_at"],
            call_id=d["call_id"],
            verification_status=d["verification_status"],
            regenerations=d.get("regenerations", 0),
            verified_grounded=d.get("verified_grounded", False),
            advisory=d.get("advisory", "unavailable"),
        )


def path_for(object_key: str, answer_dir: str = ANSWER_DIR) -> str:
    return os.path.join(answer_dir, f"{object_key}.json")


def load(object_key: str, answer_dir: str = ANSWER_DIR) -> Optional[CachedAnswer]:
    """
    The committed answer for one object, or None if none has been frozen.

    None is an ordinary outcome, not an error. Before the generation task has
    been run there is no cache, and the caller falls through to a live or floor
    call so the page works in the meantime.
    """
    path = path_for(object_key, answer_dir)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return CachedAnswer.from_dict(json.load(fh))


def save(answer: CachedAnswer, answer_dir: str = ANSWER_DIR) -> str:
    """Freeze one watched generation. Used by the generation script, not by the app."""
    os.makedirs(answer_dir, exist_ok=True)
    path = path_for(answer.object_key, answer_dir)
    with open(path, "w") as fh:
        fh.write(json.dumps(answer.to_dict(), indent=2) + "\n")
    return path
