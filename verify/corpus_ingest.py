"""
verify/corpus_ingest.py — Bob's raw submission to the canonical reject corpus.

Bob writes tests/corpus/bob_submission.raw.jsonl black-box: the shape of each
attack and why the token is wrong, in its own words, and no reason code. This
pass turns that into tests/corpus/adversarial.jsonl, which is what the tests
read. The separation is the point. The canonical file is the answer sheet, and
an author who writes it directly is sitting the exam and marking it.

What this does, and only this:

  1. Pulls cases held out by hand, recording each one's reason in the
     quarantine file rather than deleting it. A case removed without a trace is
     indistinguishable from a case that was never written.
  2. Repairs approximate span offsets mechanically. The brief tells Bob not to
     verify them, so this verifies them.
  3. Maps each attack_shape to its reason code.
  4. Triages the misattribute shape, which is the one that does not map
     cleanly, because a real number attached to the wrong result is mostly
     invisible to a membership test.

It contains no gate logic and decides nothing about whether the gate is right.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from verify.corpus import (
    CORPUS_DIR, FIXTURE_DIR, RAW_SUBMISSION_FILE, ADVERSARIAL_FILE,
    _parse_raw_case,
)

QUARANTINE_FILE = os.path.join(CORPUS_DIR, "quarantine.jsonl")
KNOWN_LIMITS_FILE = os.path.join(CORPUS_DIR, "known_limits.jsonl")

# ---------------------------------------------------------------------------
# Held out by hand, with the reason recorded
# ---------------------------------------------------------------------------
#
# Each entry is a judgement someone made and had to justify. They are listed
# here rather than removed from the raw file, so the raw submission stays
# exactly as Bob wrote it and the removals stay auditable.

HELD_OUT: Dict[str, str] = {
    "bob-005": (
        "Contaminated and false. The 'why' field reasons about the rendering "
        "ladder ('the manifest allows only 26.286 as a 4-sig-fig rendering'), "
        "which is withheld from the redacted view, and it reasons wrongly: "
        "26.29 is a pinned rung of validate.frame_gate.computed, as is the "
        "0.17 the same sentence quotes. The explanation is fully grounded, so "
        "it is an accept case wearing a reject label."
    ),
    "bob-011": (
        "Contaminated and false. The 'why' field names the ladder and then "
        "concedes the attack may not be one: 'which allows 0.044 as a "
        "rendering of 0.04386 - but verify'. It does allow it. 0.044 is the "
        "pinned sub-0.1 rung, and grounding that sentence is the behaviour the "
        "gate is required to have."
    ),
    "bob-030": (
        "Dropped rather than repaired. The reasoning is right, 2.701 is a "
        "percentage carrying km/s, but the span points at the unit rather than "
        "the number, so the case needs both a respan and a rewritten "
        "explanation to become valid. A case that takes an author's rewrite to "
        "stand is no longer the author's blind case. The wrong-unit shape "
        "still meets its floor of six without it."
    ),
}


# ---------------------------------------------------------------------------
# Shape to reason code
# ---------------------------------------------------------------------------

SHAPE_TO_REASON = {
    "fabricate": "fabricated-number",
    "nudge": "plausible-rounding",
    "wrong unit": "wrong-unit",
    "wrong frame": "frame-mismatch",
    "disguise": "label-disguise",
    "inflate": "precision-inflation",
    "spell out": "spelled-out-quantity",
    "malform": "unparseable",
    # "misattribute" is deliberately absent. It is triaged, not mapped.
}

# Which side of the published/computed seam a sentence is claiming.
COMPUTED_MARKERS = (
    "the solver", "solver's", "solver finds", "solver computed", "hits ",
    "hits computes", "computed by", "as computed", "we compute", "calculated",
)
PUBLISHED_MARKERS = (
    "published", "hein", "lyra", "the paper", "et al", "reported", "reports",
    "fig.", "figure", "p.55", "the source", "benchmark",
)
SENTENCE_SPLIT = re.compile(r"[.;:]\s+|\n")

# A period inside one of these does not end a sentence. Without this the
# splitter cuts "Hein et al. report 703" and "the paper's Fig. 6 has 111.4 AU"
# in half and strands the provenance marker in the previous fragment, which
# makes a correctly attributed figure look unattributed. The accept corpus
# caught exactly that.
NON_TERMINAL_ABBREVIATIONS = (
    "et al.", "fig.", "eq.", "p.", "pp.", "col.", "sec.", "no.", "vol.",
    "cf.", "e.g.", "i.e.", "approx.", "ref.",
)


def _sentence_boundaries(text: str) -> List[int]:
    """Where sentences actually start, abbreviations not counted as endings."""
    out = [0]
    for m in SENTENCE_SPLIT.finditer(text):
        prefix = text[:m.start() + 1].lower()
        if any(prefix.endswith(a) for a in NON_TERMINAL_ABBREVIATIONS):
            continue
        out.append(m.end())
    return out

UNIT_PATTERNS = (
    ("km^2/s^2", ("km^2/s^2", "km2/s2", "km²/s²")),
    ("km/s", ("km/s", "km/s^2", "kilometres per second", "kilometers per second")),
    ("AU", (" AU", " au")),
    ("d", (" days", " day")),
    ("yr", (" years", " year", " yr")),
    ("%", ("%", "percent")),
)
FRAME_WORDS = {
    "heliocentric": "heliocentric",
    "earth-relative": "earth_relative",
    "earth-departure": "earth_relative",
    "target-relative": "target_relative",
    "relative to the sun": "heliocentric",
}


@dataclass
class Outcome:
    case_id: str
    expect_reason: str
    triage_rule: str = ""
    note: str = ""
    offset_repaired: bool = False
    known_limit: str = ""
    token: str = ""          # the token the triage cites, when it names one
    token_pos: int = -1


# ---------------------------------------------------------------------------
# Offset repair
# ---------------------------------------------------------------------------

def repair_spans(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, Optional[str]]:
    """
    Bring approximate offsets onto their token.

    Repaired only when the span's text occurs exactly once in the explanation,
    because that is the only case with a single right answer. Zero or several
    occurrences is quarantined, not guessed: a span pointing at the wrong one
    of two identical tokens would make a wrong rejection look like a right one.
    """
    text = raw["explanation"]
    repaired = False
    out_spans = []
    for s in raw.get("offending_spans") or []:
        want = s["text"]
        if text[s["start"]:s["end"]] == want:
            out_spans.append(dict(s))
            continue
        hits = [m.start() for m in re.finditer(re.escape(want), text)]
        if len(hits) == 1:
            out_spans.append({"text": want, "start": hits[0],
                              "end": hits[0] + len(want)})
            repaired = True
        elif not hits:
            return raw, False, (
                f"span text {want!r} does not occur in the explanation, so "
                "there is nothing to repair it onto")
        else:
            return raw, False, (
                f"span text {want!r} occurs {len(hits)} times; repairing it "
                "would be a guess about which occurrence the attack means")
    out = dict(raw)
    out["offending_spans"] = out_spans
    return out, repaired, None


# ---------------------------------------------------------------------------
# Misattribute triage
# ---------------------------------------------------------------------------

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")

# Every spelling of every unit, longest first, so km^2/s^2 is masked before
# km/s can match inside it.
ALL_UNIT_SPELLINGS = sorted(
    {sp for _, spellings in UNIT_PATTERNS for sp in spellings},
    key=len, reverse=True)


def _mask_units(text: str) -> str:
    """
    Blank out unit strings, preserving length so offsets stay valid.

    Without this the digits inside km^2/s^2 read as numbers, and a bare "2"
    matches a real manifest entry. The same trap catches v_inf2, C3 and 1I,
    which the NUMBER pattern excludes by refusing a digit adjacent to a word
    character.
    """
    masked = text
    for sp in ALL_UNIT_SPELLINGS:
        start = 0
        while True:
            i = masked.find(sp, start)
            if i < 0:
                break
            masked = masked[:i] + ("\x00" * len(sp)) + masked[i + len(sp):]
            start = i + len(sp)
    return masked


def all_tokens(text: str) -> List[Tuple[str, int, int]]:
    """
    Every numeric or date token in the text, as (token, start, end).

    The single tokenizer. The extraction rule and the manifest lookup both use
    it, so they cannot disagree about what counts as a number.

    Three traps it closes. Units are masked first, so the digits inside
    km^2/s^2 are not numbers. An ISO date is one token, so 2018-06-04 does not
    also yield a bare 06 that no explanation wrote. And a digit fused to a word
    character is part of an identifier, not a quantity, which is what keeps C3,
    1I, J2000 and v_inf2 out.
    """
    masked = _mask_units(text)
    iso = [(m.start(), m.end()) for m in ISO_DATE.finditer(masked)]
    out = [(m.group(), m.start(), m.end()) for m in ISO_DATE.finditer(masked)]
    for m in NUMBER.finditer(masked):
        if any(a <= m.start() < b for a, b in iso):
            continue
        out.append((m.group().replace(",", ""), m.start(), m.end()))
    return sorted(out, key=lambda t: t[1])


def _tokens_in_manifest(text: str, index) -> List[Tuple[str, int, list]]:
    """The manifest renderings actually quoted in the explanation."""
    return [(tok, start, index[tok])
            for tok, start, _ in all_tokens(text) if tok in index]


def _unit_after(text: str, end: int) -> Optional[str]:
    """
    The unit attached to the token that ends at `end`, if any.

    Only what immediately follows counts. A unit further along the sentence
    belongs to a later number: in "C3 for 2027 is 1331.16 km^2/s^2" the energy
    unit is the C3's, not the year's.
    """
    tail = text[end:end + 24]
    stripped = tail.lstrip()
    if not stripped:
        return None
    for canonical, spellings in UNIT_PATTERNS:
        for sp in spellings:
            probe = sp.lstrip()
            if stripped.startswith(probe):
                return canonical
    return None


def _sentence_at(text: str, pos: int) -> Tuple[str, int]:
    """The sentence containing `pos`, and where it starts."""
    starts = _sentence_boundaries(text)
    start = max(s for s in starts if s <= pos)
    later = [s for s in starts if s > pos]
    end = later[0] if later else len(text)
    return text[start:end], start


def sentence_before(text: str, pos: int) -> str:
    """The part of the token's sentence that precedes it."""
    sentence, start = _sentence_at(text, pos)
    return sentence[:pos - start]


def sentence_after(text: str, pos: int) -> str:
    """The part of the token's sentence from the token onward."""
    sentence, start = _sentence_at(text, pos)
    return sentence[pos - start:]


# Public aliases. The gate imports these so its tokenizer and sentence scope
# are the same code the triage used, and the two cannot drift into disagreeing
# about what counts as a quoted number.
tokens_in_manifest = _tokens_in_manifest
sentence_at = _sentence_at


def _nearby(text: str, pos: int, markers) -> bool:
    """
    Whether an attribution marker applies to the token at `pos`.

    Scoped to the sentence, not to a character window. A window has an
    arbitrary edge, and the edge landed badly: at 60 characters it clipped
    "The" off "The solver confirms" and lost the marker entirely. A sentence is
    the unit an attribution claim actually spans.
    """
    sentence, _ = _sentence_at(text, pos)
    low = sentence.lower()
    return any(mk in low for mk in markers)


def _marker_before(text: str, pos: int, markers) -> bool:
    """
    An attribution marker introducing the token, earlier in its sentence.

    A published figure ought to be introduced as published. Asking instead
    whether a published marker appears anywhere in the sentence gets
    "Sample B's v_inf2 of 0.6 km/s ... confirms the Hein et al. result" wrong:
    the marker is real but it attaches to the result at the end, not to the 0.6
    being passed off as the computed v_inf2.
    """
    return any(mk in sentence_before(text, pos).lower() for mk in markers)


def _marker_after(text: str, pos: int, markers) -> bool:
    """
    An attribution marker appearing after the token in the same sentence.

    This is the apposition case: "1331.16 km^2/s^2, which HITS labels as a
    published benchmark value". The sentence names both sides, so asking
    whether the other side is merely present would find both and decide
    nothing; what matters is that the label is being applied to this token.
    """
    return any(mk in sentence_after(text, pos).lower() for mk in markers)


def triage_misattribute(raw: Dict[str, Any], manifest) -> Outcome:
    """
    Decide what a misattribute case actually is.

    Four outcomes, in order. The last is the important one: a real number
    attached to the wrong result, in the right unit and the right frame, is
    invisible to a membership test. Those cases are not thrown away and are not
    counted as rejections the gate will make. They are recorded as known
    limits, so the hole is visible and tested rather than silent.
    """
    text = raw["explanation"]
    index = manifest.index()
    cid = raw["case_id"]
    span_text = raw["offending_spans"][0]["text"]

    present = _tokens_in_manifest(text, index)

    # 1. The span is a number the manifest does not carry: membership rejects it
    #    already, no triage needed.
    if span_text not in index and re.fullmatch(r"[\d.,\-]+", span_text):
        return Outcome(cid, "fabricated-number", "1: span is not in the manifest")

    # 2. The published/computed seam. Frozen membership accepts every one of
    #    these: the token is in the manifest with a matching unit and frame, so
    #    nothing the gate does today rejects them. They are limits, not
    #    rejections, and they are tagged separately from rule 4 because the
    #    seam IS decidable from entry.kind plus an attribution phrase, and
    #    verify.groundedness.check_attribution now decides it, so these are
    #    rejections. Rule 4's cases cannot be reached that way and stay limits.
    #
    #    Which token to cite, when a sentence mixes sides: prefer the
    #    published-only one, because that is the value being passed off as the
    #    system's own. Only if there is none does the computed value a later
    #    marker mislabels get cited.
    published_only = [(r, p, e) for r, p, e in present
                      if {x.kind for x in e} == {"published"}]
    for rendering, pos, entries in published_only:
        if not _marker_before(text, pos, PUBLISHED_MARKERS):
            return Outcome(
                cid, "attribution-mismatch",
                "2: published value presented as the solver's own",
                token=rendering, token_pos=pos,
                note=f"{rendering!r} is published-only "
                     f"({[e.id for e in entries][0]}); membership alone accepts "
                     "it, since the token, unit and frame all match")

    for rendering, pos, entries in present:
        kinds = {e.kind for e in entries}
        if kinds and kinds <= {"computed", "derived"}:
            if _marker_after(text, pos, PUBLISHED_MARKERS):
                return Outcome(
                    cid, "attribution-mismatch",
                    "2: computed value presented as published",
                    token=rendering, token_pos=pos,
                    note=f"{rendering!r} is computed "
                         f"({[e.id for e in entries][0]}); membership alone "
                         "accepts it, since the token, unit and frame all match")

    # 3. Separable on unit or frame, so an existing code already covers it.
    for rendering, pos, entries in present:
        units = {e.unit for e in entries}
        attached = _unit_after(text, pos + len(rendering))
        if attached and attached not in units:
            return Outcome(
                cid, "wrong-unit", "3: unit attached to the token conflicts",
                note=f"{rendering!r} carries {sorted(units)}, "
                     f"sentence attaches {attached!r}")
        frames = {e.frame for e in entries}
        low = text.lower()
        for word, frame in FRAME_WORDS.items():
            if word in low and frames and frame not in frames and "n_a" not in frames:
                return Outcome(
                    cid, "frame-mismatch", "3: frame in the sentence conflicts",
                    note=f"{rendering!r} is {sorted(frames)}, "
                         f"sentence says {word!r}")

    # 4. Membership cannot see it.
    return Outcome(
        cid, "", "4: invisible to a membership test",
        known_limit="result-binding",
        note="every token is in the manifest with a matching unit and frame; "
             "the wrongness is in which result the number is attached to")


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------

def ingest(raw_path: str = RAW_SUBMISSION_FILE, write: bool = True) -> Dict[str, Any]:
    from solver.manifest import Manifest

    rows = []
    with open(raw_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if line.strip():
                rows.append((lineno, json.loads(line)))

    manifests: Dict[str, Any] = {}

    canonical, quarantined, known_limits = [], [], []
    outcomes: List[Outcome] = []

    for lineno, raw in rows:
        cid = raw.get("case_id", f"line {lineno}")

        if cid in HELD_OUT:
            quarantined.append({**raw, "quarantine_reason": HELD_OUT[cid],
                                "quarantined_by": "corpus owner, before ingest"})
            continue

        repaired_raw, was_repaired, problem = repair_spans(raw)
        if problem:
            quarantined.append({**raw, "quarantine_reason": problem,
                                "quarantined_by": "ingest, offset repair"})
            continue

        try:
            _parse_raw_case(repaired_raw, raw_path, lineno)
        except Exception as exc:
            quarantined.append({**raw, "quarantine_reason": f"schema: {exc}",
                                "quarantined_by": "ingest, schema validation"})
            continue

        ref = repaired_raw["manifest_ref"]
        if ref not in manifests:
            with open(os.path.join(FIXTURE_DIR, ref), encoding="utf-8") as fh:
                manifests[ref] = Manifest.from_json(fh.read())
        manifest = manifests[ref]

        shape = repaired_raw["attack_shape"]
        if shape == "misattribute":
            outcome = triage_misattribute(repaired_raw, manifest)
        else:
            outcome = Outcome(cid, SHAPE_TO_REASON[shape], "mapped")
        outcome.offset_repaired = was_repaired
        outcomes.append(outcome)

        spans = repaired_raw["offending_spans"]
        if outcome.token:
            # The span moves to the token the attribution check will cite. Bob
            # often flagged the attributing phrase ("as computed by HITS"),
            # which reads correctly but is not the thing the gate rejects.
            spans = [{"text": outcome.token, "start": outcome.token_pos,
                      "end": outcome.token_pos + len(outcome.token)}]

        record = {
            "case_id": cid,
            "author": repaired_raw["author"],
            "created": repaired_raw["created"],
            "manifest_ref": ref,
            "explanation": repaired_raw["explanation"],
            "offending_spans": spans,
            "attack_shape": shape,
            "why": repaired_raw["why"],
            "offset_repaired": was_repaired,
        }

        if outcome.known_limit:
            known_limits.append({**record, "expect": "accept",
                                 "known_limit": outcome.known_limit,
                                 "triage_rule": outcome.triage_rule,
                                 "notes": outcome.note})
        else:
            canonical.append({**record, "expect": "reject",
                              "expect_reason": outcome.expect_reason,
                              "triage_rule": outcome.triage_rule,
                              "notes": outcome.note})

    if write:
        _write(ADVERSARIAL_FILE, canonical)
        _write(QUARANTINE_FILE, quarantined)
        _write(KNOWN_LIMITS_FILE, known_limits)

    return {"canonical": canonical, "quarantined": quarantined,
            "known_limits": known_limits, "outcomes": outcomes,
            "raw_count": len(rows)}


def _write(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def report(result: Dict[str, Any]) -> str:
    from collections import Counter
    L = []
    L.append(f"raw submission        : {result['raw_count']} cases")
    L.append(f"canonical reject corpus: {len(result['canonical'])}")
    L.append(f"quarantined            : {len(result['quarantined'])}")
    L.append(f"known limits           : {len(result['known_limits'])}")
    L.append("")
    L.append("reason codes assigned:")
    for code, n in sorted(Counter(c["expect_reason"] for c in result["canonical"]).items()):
        L.append(f"  {code:24s} {n}")
    L.append("")
    repaired = [c["case_id"] for c in result["canonical"] + result["known_limits"]
                if c.get("offset_repaired")]
    L.append(f"offsets repaired       : {len(repaired)}")
    L.append(f"  {', '.join(repaired)}" if repaired else "")
    L.append("")
    from collections import Counter as _C
    tags = _C(k["known_limit"] for k in result["known_limits"])
    L.append("accepted limits, by tag:")
    for tag, n in sorted(tags.items()):
        L.append(f"  {tag:24s} {n}")
    L.append("")
    L.append("misattribute triage:")
    for o in result["outcomes"]:
        if o.triage_rule and o.triage_rule != "mapped":
            label = o.expect_reason or f"KNOWN LIMIT ({o.known_limit})"
            L.append(f"  {o.case_id:9s} rule {o.triage_rule}")
            L.append(f"            -> {label}")
            if o.note:
                L.append(f"            {o.note}")
    L.append("")
    L.append("quarantined cases:")
    for q in result["quarantined"]:
        L.append(f"  {q['case_id']:9s} [{q['quarantined_by']}]")
        L.append(f"            {q['quarantine_reason'][:150]}")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report without writing any file")
    args = ap.parse_args()
    res = ingest(write=not args.dry_run)
    print(report(res))
