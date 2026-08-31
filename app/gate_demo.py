"""
app/gate_demo.py — the number check, run live, in front of the reader.

CLAUDE.md's first non-negotiable is that every number is computed and never
generated, and that a deterministic check compares every numeric token in an
explanation against the solver's output before the explanation is returned.
That is a claim about machinery a reader cannot see. This module makes it
something they can watch happen: the same `verify.groundedness.check` the
serving path runs, applied to two candidates, one of which has had a single
figure replaced with one the solver never produced.

## Why the fabrication is a digit swap and not a computed value

There is no arithmetic in this package. A demo that derived its fake number by
scaling a real one would be a surface computing a figure, which is the exact
thing the architecture forbids, and it would be doing it in the module whose
whole purpose is to show that figures are not made up here. So the injection is
lexical: one digit of one canonical rendering is replaced with a different
digit, and the result is checked against the manifest's own rendering index to
confirm the solver never emitted it. That is also the more faithful
fabrication. A model does not invent a number by multiplying; it transposes a
digit, and the transposed digit is exactly the failure that is hard to catch by
eye and trivial for the gate.

## Why the choice is fixed rather than random

A judge who reloads the page sees the same demonstration. A random injection
would make the endpoint a different exhibit on every request, and a
disagreement between two people looking at it would be unresolvable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agent import template
from verify.groundedness import check

# The entry to fabricate against, in order of preference. Departure C3 is the
# headline figure of an intercept answer: it opens the explanation and it is
# the number a reader is most likely to carry away, so it is the one worth
# showing the gate catching.
PREFERRED_ENTRY_IDS = ("solve.c3", "solve.dv_depart", "solve.v_inf2")

# The digit substituted in. Fixed so the exhibit is the same on every reload.
_SWAP = {"0": "8", "1": "7", "2": "9", "3": "8", "4": "9",
         "5": "3", "6": "2", "7": "1", "8": "3", "9": "4"}


def _permitted(manifest) -> set:
    """Every string the manifest renders, across all entries."""
    return set(manifest.index())


def _fabricate(rendering: str, permitted: set) -> Optional[str]:
    """
    A near-miss of one rendering that the manifest does not permit.

    Walks the digits from the least significant end, because a transposition in
    the last place is the one that survives a careless read. Returns None if
    every single-digit variant happens to be a string the manifest renders,
    which would mean the near-miss is a real figure and showing it rejected
    would be a lie.
    """
    for i in range(len(rendering) - 1, -1, -1):
        ch = rendering[i]
        if not ch.isdigit():
            continue
        candidate = rendering[:i] + _SWAP[ch] + rendering[i + 1:]
        if candidate != rendering and candidate not in permitted:
            return candidate
    return None


def _choose(manifest, text: str) -> Tuple[str, str, str]:
    """
    The entry to fabricate against, its canonical rendering, and the fake.

    The entry has to satisfy three things at once: it is a number, its
    canonical rendering actually appears in the text (replacing a string that
    is not there would produce an identical candidate and a demonstration of
    nothing), and a near-miss of it exists that the manifest does not render.
    """
    permitted = _permitted(manifest)
    ordered = [e for i in PREFERRED_ENTRY_IDS for e in manifest.entries if e.id == i]
    ordered += [e for e in manifest.entries if e not in ordered]

    for e in ordered:
        if not e.is_number:
            continue
        real = e.canonical
        if real not in text:
            continue
        fake = _fabricate(real, permitted)
        if fake is not None:
            return e.id, real, fake

    raise RuntimeError(
        "no entry in this manifest offers a fabricable near-miss that appears "
        "in the explanation. The demo would otherwise show a rejection it did "
        "not actually cause.")


def _verdict_dict(verdict) -> Dict[str, Any]:
    """The gate's verdict, serialized whole, findings included."""
    return {
        "grounded": verdict.grounded,
        "checks_run": list(verdict.checks_run),
        "advisory": verdict.advisory,
        "findings": [
            {"text": f.text, "reason": f.reason, "position": f.start,
             "note": f.note}
            for f in verdict.findings
        ],
    }


def gate_demo(frozen) -> Dict[str, Any]:
    """
    Two candidates and the gate's verdict on each.

    The grounded one is the text the service actually serves for this object,
    not a specimen written for the demo, so what a reader watches pass is the
    same string /explain returns. The fabricated one differs from it by one
    digit of one figure and nothing else.
    """
    manifest = frozen.manifest
    grounded_text = template.explain(manifest)

    entry_id, real, fake = _choose(manifest, grounded_text)
    fabricated_text = grounded_text.replace(real, fake, 1)

    grounded_verdict = check(grounded_text, manifest)
    fabricated_verdict = check(fabricated_text, manifest)

    return {
        "object": frozen.key,
        "designation": frozen.designation,
        "call_id": frozen.call_id,
        "what_this_shows": (
            "The same deterministic check that runs before any explanation is "
            "served, applied to the served text and to one copy of it with a "
            "single digit changed. No model and no credential is involved: the "
            "check compares numeric tokens against the manifest of what the "
            "solver computed, and the comparison is what decides."
        ),
        "injection": {
            "entry_id": entry_id,
            "label": manifest.by_id(entry_id).label,
            "unit": manifest.by_id(entry_id).unit,
            "solver_value": real,
            "injected_token": fake,
            "method": (
                "one digit of the canonical rendering replaced, first "
                "occurrence only. Lexical, not computed: this package performs "
                "no arithmetic."
            ),
        },
        "grounded": {
            "text": grounded_text,
            "verdict": _verdict_dict(grounded_verdict),
        },
        "fabricated": {
            "text": fabricated_text,
            "injected_token": fake,
            "verdict": _verdict_dict(fabricated_verdict),
        },
    }
