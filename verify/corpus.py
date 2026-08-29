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

# Reject cases Bob could not author blind. derived-not-emitted needs to know
# what the manifest omits; stale-number needs values from a retrieval Bob never
# saw. Both are withheld from the brief on purpose, so they are written here.
WHITEBOX_FILE = os.path.join(CORPUS_DIR, "adversarial_whitebox.jsonl")

# What Bob writes, black-box. Validated by load_raw_submission() below, which
# knows nothing about reason codes. See docs/BOB_BRIEF_CORPUS.md.
RAW_SUBMISSION_FILE = os.path.join(CORPUS_DIR, "bob_submission.raw.jsonl")

# Closed vocabulary (docs/CORPUS.md). A case outside it fails to load rather
# than being silently accepted with a reason nothing will ever check.
REJECT_REASONS = (
    # Covers a near-miss, a correct derivation the manifest never emitted, a
    # value from an earlier retrieval, and an outright invention. All four
    # reach the gate as a string the index does not hold, and separating them
    # needs arithmetic the gate is forbidden. See docs/MANIFEST.md, "What the
    # no-arithmetic rule costs".
    "fabricated-number",
    "wrong-unit",
    "frame-mismatch",
    "label-disguise",
    "precision-inflation",
    "spelled-out-quantity",
    "unparseable",
    # A value from this manifest attributed to the wrong side of the
    # published/computed seam. Produced by verify.groundedness.check_attribution.
    "attribution-mismatch",
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
    cases = (load_cases(ADVERSARIAL_FILE) + load_cases(WHITEBOX_FILE)
             + load_cases(GROUNDED_FILE))
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


# ---------------------------------------------------------------------------
# The raw submission: Bob's schema, on its own terms
# ---------------------------------------------------------------------------
#
# Everything below validates docs/BOB_BRIEF_CORPUS.md's schema and nothing else.
# It deliberately knows no reason codes. The brief asks Bob to describe the
# SHAPE of an attack and why the token is wrong, in its own words, and to leave
# the gate's vocabulary alone; translation into that vocabulary is the ingest
# pass's job, on the corpus owner's side, later.
#
# That isolation is the point, and it exists because it was breached. A brief
# told Bob to emit attack_shape and why, but nothing in the tree could load such
# a file, so Bob read the canonical loader, found expect_reason, and wrote to
# that instead. The corpus that came back was shaped by the gate's own
# vocabulary, which is exactly what a black-box corpus must not be. A schema
# with no loader is a schema an author will route around.
#
# REJECT_REASONS is not imported here, not referenced here, and must not be.
# tests/test_corpus_raw.py enforces that by walking this module's AST.

# The nine shapes named in the brief, spelled as the brief spells them.
ATTACK_SHAPES = (
    "fabricate",
    "nudge",
    "wrong unit",
    "wrong frame",
    "disguise",
    "misattribute",
    "inflate",
    "spell out",
    "malform",
)

# The brief's schema, exactly. A field outside this set is not something Bob was
# asked for, and accepting it silently is how a schema drifts.
RAW_FIELDS = frozenset({
    "case_id", "author", "created", "manifest_ref", "explanation",
    "expect", "attack_shape", "offending_spans", "why",
})


class RawSubmissionError(ValueError):
    """A raw submission that does not satisfy docs/BOB_BRIEF_CORPUS.md."""


@dataclass(frozen=True)
class RawCase:
    """
    One case as Bob wrote it. Carries no reason code, by design.

    Deliberately not a `Case`: the canonical schema the tests read is not
    loosened to accommodate this one, and a RawCase cannot be handed to the
    runner by accident.
    """
    case_id: str
    author: str
    created: str
    manifest_ref: str
    explanation: str
    expect: str
    attack_shape: str
    why: str
    offending_spans: List[Span] = field(default_factory=list)
    source_file: str = ""


def _parse_raw_case(raw: Dict[str, Any], source_file: str, lineno: int) -> RawCase:
    where = f"{os.path.basename(source_file)}:{lineno}"

    present = set(raw)

    # Called out on its own, ahead of the general unknown-field check, because
    # it is the specific way this went wrong once and the fix is not obvious
    # from a generic message.
    if "expect_reason" in present:
        raise RawSubmissionError(
            f"{where}: carries 'expect_reason'. A raw submission does not "
            "assign one. Describe the attack with 'attack_shape' and 'why'; "
            "the reason code is assigned later, by the corpus owner, and a "
            "submission that assigns its own was written against the gate's "
            "vocabulary rather than blind to it")

    unknown = present - RAW_FIELDS
    if unknown:
        raise RawSubmissionError(
            f"{where}: fields not in the brief's schema: {sorted(unknown)}. "
            f"Expected exactly {sorted(RAW_FIELDS)}")

    missing = RAW_FIELDS - present
    if missing:
        raise RawSubmissionError(
            f"{where}: missing required fields: {sorted(missing)}")

    if raw["author"] != "bob":
        raise RawSubmissionError(
            f"{where}: author is {raw['author']!r}. The raw submission is Bob's "
            "black-box work; anything else belongs in a white-box corpus file")

    if raw["expect"] != "reject":
        raise RawSubmissionError(
            f"{where}: expect is {raw['expect']!r}. The raw submission is reject "
            "cases only; accept cases are authored white-box")

    if raw["attack_shape"] not in ATTACK_SHAPES:
        raise RawSubmissionError(
            f"{where}: attack_shape {raw['attack_shape']!r} is not one of "
            f"{list(ATTACK_SHAPES)}")

    if not str(raw["why"]).strip():
        raise RawSubmissionError(
            f"{where}: 'why' is empty. It is the whole of what Bob records "
            "about the failure, and the ingest pass reads it")

    raw_spans = raw["offending_spans"] or []
    if not raw_spans:
        raise RawSubmissionError(
            f"{where}: no offending span. Without one, a gate that trips over "
            "an unrelated token looks the same as a gate that caught the attack")

    spans: List[Span] = []
    for s in raw_spans:
        for key in ("text", "start", "end"):
            if key not in s:
                raise RawSubmissionError(f"{where}: span missing {key!r}")
        span = Span(text=s["text"], start=int(s["start"]), end=int(s["end"]))
        actual = raw["explanation"][span.start:span.end]
        if actual != span.text:
            raise RawSubmissionError(
                f"{where}: span offsets do not match the text. "
                f"explanation[{span.start}:{span.end}] is {actual!r}, "
                f"the case says {span.text!r}")
        spans.append(span)

    fixture = os.path.join(FIXTURE_DIR, raw["manifest_ref"])
    if not os.path.exists(fixture):
        raise RawSubmissionError(
            f"{where}: manifest_ref {raw['manifest_ref']!r} is not a committed "
            f"fixture in {FIXTURE_DIR}")

    return RawCase(
        case_id=raw["case_id"],
        author=raw["author"],
        created=raw["created"],
        manifest_ref=raw["manifest_ref"],
        explanation=raw["explanation"],
        expect=raw["expect"],
        attack_shape=raw["attack_shape"],
        why=raw["why"],
        offending_spans=spans,
        source_file=source_file,
    )


def load_raw_submission(path: str = RAW_SUBMISSION_FILE) -> List[RawCase]:
    """
    Load and validate Bob's raw submission.

    A missing file yields an empty list, not an error: the file does not exist
    until Bob has written it, and that shortfall is reported by the corpus
    bars rather than by a crash here.
    """
    if not os.path.exists(path):
        return []
    cases: List[RawCase] = []
    seen = set()
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RawSubmissionError(
                    f"{os.path.basename(path)}:{lineno}: not valid JSON: {exc}"
                ) from exc
            case = _parse_raw_case(raw, path, lineno)
            if case.case_id in seen:
                raise RawSubmissionError(
                    f"{os.path.basename(path)}:{lineno}: duplicate case_id "
                    f"{case.case_id!r}")
            seen.add(case.case_id)
            cases.append(case)
    return cases
