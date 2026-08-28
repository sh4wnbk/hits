"""
verify/corpus.py — loading and validating adversarial corpus cases.

Format: docs/CORPUS.md.

This module loads and checks the SHAPE of a case. It contains no part of the
gate's matching policy, and importing it tells you nothing about how a token is
matched against the manifest.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CORPUS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "tests", "corpus")
FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "tests", "fixtures", "manifests")

ADVERSARIAL_FILE = os.path.join(CORPUS_DIR, "adversarial.jsonl")
GROUNDED_FILE = os.path.join(CORPUS_DIR, "grounded.jsonl")

# Closed vocabulary (docs/CORPUS.md). A case outside it fails to load rather
# than being silently accepted with a reason nothing will ever check.
REJECT_REASONS = (
    "fabricated-number",
    "plausible-rounding",
    "derived-not-emitted",
    "wrong-unit",
    "frame-mismatch",
    "label-disguise",
    "cross-call-number",
    "stale-number",
    "precision-inflation",
    "spelled-out-quantity",
    "unparseable",
)

AUTHORS = ("bob", "claude-code")


class CorpusError(ValueError):
    """A case that does not satisfy the format in docs/CORPUS.md."""


@dataclass(frozen=True)
class Span:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Case:
    case_id: str
    author: str
    created: str
    manifest_ref: str
    explanation: str
    expect: str
    notes: str = ""
    expect_reason: Optional[str] = None
    offending_spans: List[Span] = field(default_factory=list)
    source_file: str = ""

    @property
    def is_reject(self) -> bool:
        return self.expect == "reject"


def _parse_case(raw: Dict[str, Any], source_file: str, lineno: int) -> Case:
    where = f"{os.path.basename(source_file)}:{lineno}"

    for required in ("case_id", "author", "created", "manifest_ref",
                     "explanation", "expect"):
        if required not in raw:
            raise CorpusError(f"{where}: missing required field {required!r}")

    if raw["author"] not in AUTHORS:
        raise CorpusError(f"{where}: author {raw['author']!r} not in {AUTHORS}")
    if raw["expect"] not in ("accept", "reject"):
        raise CorpusError(f"{where}: expect must be 'accept' or 'reject'")

    spans: List[Span] = []
    if raw["expect"] == "reject":
        reason = raw.get("expect_reason")
        if reason not in REJECT_REASONS:
            raise CorpusError(
                f"{where}: expect_reason {reason!r} outside the closed "
                f"vocabulary {REJECT_REASONS}")
        raw_spans = raw.get("offending_spans") or []
        if not raw_spans:
            raise CorpusError(
                f"{where}: a reject case must name at least one offending span, "
                "otherwise a gate that trips over an unrelated token looks the "
                "same as a gate that caught the attack")
        for s in raw_spans:
            span = Span(text=s["text"], start=int(s["start"]), end=int(s["end"]))
            actual = raw["explanation"][span.start:span.end]
            if actual != span.text:
                raise CorpusError(
                    f"{where}: span offsets do not match the text. "
                    f"explanation[{span.start}:{span.end}] is {actual!r}, "
                    f"the case says {span.text!r}")
            spans.append(span)
    else:
        if raw.get("expect_reason"):
            raise CorpusError(f"{where}: an accept case carries no expect_reason")

    fixture = os.path.join(FIXTURE_DIR, raw["manifest_ref"])
    if not os.path.exists(fixture):
        raise CorpusError(
            f"{where}: manifest_ref {raw['manifest_ref']!r} is not a committed "
            f"fixture in {FIXTURE_DIR}")

    return Case(
        case_id=raw["case_id"],
        author=raw["author"],
        created=raw["created"],
        manifest_ref=raw["manifest_ref"],
        explanation=raw["explanation"],
        expect=raw["expect"],
        notes=raw.get("notes", ""),
        expect_reason=raw.get("expect_reason"),
        offending_spans=spans,
        source_file=source_file,
    )


def load_cases(path: str) -> List[Case]:
    """Load one corpus file. Missing file yields an empty list, not an error:
    Bob's file is empty until Bob has written it, and the runner reports that
    as a shortfall rather than as a crash."""
    if not os.path.exists(path):
        return []
    cases: List[Case] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CorpusError(
                    f"{os.path.basename(path)}:{lineno}: not valid JSON: {exc}"
                ) from exc
            cases.append(_parse_case(raw, path, lineno))
    return cases


def load_all() -> List[Case]:
    cases = load_cases(ADVERSARIAL_FILE) + load_cases(GROUNDED_FILE)
    seen = {}
    for c in cases:
        if c.case_id in seen:
            raise CorpusError(f"duplicate case_id {c.case_id!r}")
        seen[c.case_id] = c
    return cases


def load_manifest_for(case: Case):
    from solver.manifest import Manifest
    with open(os.path.join(FIXTURE_DIR, case.manifest_ref), encoding="utf-8") as fh:
        return Manifest.from_json(fh.read())
