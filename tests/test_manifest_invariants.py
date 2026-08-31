"""
tests/test_manifest_invariants.py — the invariants ManifestEntry never enforced,
checked against every committed manifest.

## Why this file exists

`ManifestEntry.is_number` returns on its first line, and five asserts are
written below that return (solver/manifest.py, the property under
`__post_init__`). They read as though they were meant to close `__post_init__`
and ended up one method too far down. Unreachable code is ordinarily a tidiness
problem; here it means five conditions that the manifest contract states have
never once been checked on any entry, on any call, since Phase 2.

CLAUDE.md records the finding and defers the fix, for a reason worth repeating:
moving the asserts could fail an entry that has been quietly out of lexicon all
along, and discovering that at import time, inside a branch doing something
else, is the worst moment to discover it. So the question "do these conditions
actually hold" is separated from the question "where should the check live",
and this file answers only the first.

It answers it against shipped data rather than against a freshly built
manifest. The four committed files are what the deployed service serves and
what the corpus is judged against; a synthetic entry proving the conditions are
satisfiable would prove nothing about them.

## Which condition matters most

The citation guard on published entries. verify/groundedness.py's attribution
check rests on published figures being tellable from computed ones, because the
failure it exists to catch is an explanation presenting the solver's own output
as though a paper had confirmed it. A published entry carrying no citation is
that distinction going soft, and it would be invisible: the entry would still
match on membership and still render, and nothing would report it.

## What this file deliberately does not do

It does not enable, move, or touch the asserts. If it is green, that is
evidence the shipped data satisfies the contract, not a decision about where
enforcement belongs. That decision is a separate change.
"""

import json
import os

import pytest

from solver import objects
from solver.frozen import load as load_frozen
from solver.manifest import FRAMES, KINDS, UNITS, Manifest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATE_FIXTURE = os.path.join(
    REPO_ROOT, "tests", "fixtures", "manifests", "validate_full.json")


def _committed_manifests():
    """
    Every committed manifest, named. The three frozen object envelopes and the
    validate fixture: as of this commit those are the only four in the
    repository, and the count is asserted below so a fifth cannot be added
    without this check being extended to it.
    """
    out = [(key, load_frozen(key).manifest) for key in objects.KEYS]
    with open(VALIDATE_FIXTURE) as fh:
        out.append(("validate_full", Manifest.from_dict(json.load(fh))))
    return out


COMMITTED = _committed_manifests()
ALL_ENTRIES = [(name, e) for name, m in COMMITTED for e in m.entries]


def test_the_committed_set_is_the_four_this_file_checks():
    """
    A guard on the guard. This file's value is that it covers everything
    shipped, so a new committed manifest that escaped it would quietly reopen
    the hole.
    """
    frozen_dir = os.path.join(REPO_ROOT, "data", "manifests")
    frozen_files = sorted(f for f in os.listdir(frozen_dir) if f.endswith(".json"))
    fixture_dir = os.path.join(REPO_ROOT, "tests", "fixtures", "manifests")
    fixture_files = sorted(f for f in os.listdir(fixture_dir) if f.endswith(".json"))

    assert frozen_files == ["atlas.json", "borisov.json", "oumuamua.json"]
    assert fixture_files == ["validate_full.json"]
    assert [name for name, _ in COMMITTED] == [
        "oumuamua", "borisov", "atlas", "validate_full"]
    assert len(ALL_ENTRIES) == 117, len(ALL_ENTRIES)


# ---------------------------------------------------------------------------
# The five conditions, one test each
# ---------------------------------------------------------------------------

def test_every_entry_declares_a_unit_inside_the_closed_lexicon():
    """
    UNITS is closed on purpose. A unit outside it is a string the gate's unit
    check cannot reason about, and the check would pass it silently rather
    than object.
    """
    bad = [(name, e.id, e.unit) for name, e in ALL_ENTRIES if e.unit not in UNITS]
    assert not bad, f"units outside {UNITS}: {bad}"


def test_every_entry_declares_a_frame_inside_the_closed_lexicon():
    """
    A frame outside FRAMES would make the frame-conflict check in
    verify/groundedness.py unable to tell agreement from an unrecognised
    string, and an unrecognised string does not raise, it just never conflicts.
    """
    bad = [(name, e.id, e.frame) for name, e in ALL_ENTRIES if e.frame not in FRAMES]
    assert not bad, f"frames outside {FRAMES}: {bad}"


def test_every_entry_declares_a_kind_inside_the_closed_lexicon():
    """
    kind drives attribution. An unrecognised kind is neither published nor
    computed as far as the attribution check is concerned, which is the one
    place an entry should never be able to sit.
    """
    bad = [(name, e.id, e.kind) for name, e in ALL_ENTRIES if e.kind not in KINDS]
    assert not bad, f"kinds outside {KINDS}: {bad}"


def test_every_entry_renders_at_least_one_string():
    """
    `renderings` IS the matching policy. An entry with none is a number the
    manifest holds and permits nobody to write, so an explanation quoting it
    correctly would be rejected as fabricated.
    """
    bad = [(name, e.id) for name, e in ALL_ENTRIES if not e.renderings]
    assert not bad, f"entries with no renderings: {bad}"
    for name, e in ALL_ENTRIES:
        assert e.canonical == e.renderings[0]
        assert all(isinstance(r, str) and r for r in e.renderings), (name, e.id)


def test_every_published_entry_carries_its_citation():
    """
    The one that matters most, and the reason this file was written before
    handoff 3 wires Granite.

    Attribution checking distinguishes a figure a paper published from a figure
    the solver computed, so that an explanation cannot present the solver's own
    output as externally confirmed. That distinction is only as good as the
    citations on the published entries, and an uncited published entry fails
    open: it still matches, still renders, and reports nothing.
    """
    published = [(name, e) for name, e in ALL_ENTRIES if e.kind == "published"]
    assert published, "no published entries found; this check would be vacuous"

    bad = [(name, e.id) for name, e in published if not e.citation]
    assert not bad, (
        f"published entries with no citation: {bad}. Attribution in "
        "verify/groundedness.py leans on published figures being tellable "
        "from computed ones, and an uncited one fails open.")

    for name, e in published:
        assert e.citation.strip() == e.citation, (name, e.id, repr(e.citation))
        assert len(e.citation) > 5, (name, e.id, e.citation)


# ---------------------------------------------------------------------------
# What the measurement covered
# ---------------------------------------------------------------------------

def test_the_check_is_not_vacuous():
    """
    Every condition needs entries to have been exercised on. A manifest set
    that happened to contain no published entry, or no framed entry, would make
    the green above mean less than it appears to.
    """
    kinds = {e.kind for _, e in ALL_ENTRIES}
    frames = {e.frame for _, e in ALL_ENTRIES}
    units = {e.unit for _, e in ALL_ENTRIES}

    assert "published" in kinds
    assert "computed" in kinds
    assert len(kinds) >= 5, kinds
    assert frames - {"n_a"}, "every entry is frameless; the frame check proved nothing"
    assert len(units) >= 4, units
