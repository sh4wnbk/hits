"""
tests/test_frozen_manifests.py — the committed intercept envelopes, and the
guarantee that serving one stays light.

data/manifests/*.json is the source of truth for what the service answers.
Nothing at request time reruns the solver, so these files carry the whole
weight of three claims: the numbers survive serialization, the floor's answer
about them is still grounded against them, and the call_id scoping that stops
one object's figures appearing in another object's answer survives the freeze.

The fourth test is about the deployment rather than the physics. The serving
path imports json and the standard library; the path that built these files
imports four hundred modules of numpy, astropy, hapsira and scipy. Keeping
those apart is what lets a free web instance run this at all, and an import
added carelessly to solver/manifest.py or agent/template.py would undo it
silently. So it is asserted, in a subprocess, because by the time the rest of
this suite has run numpy is long since in sys.modules and the check would pass
for the wrong reason.
"""

import json
import os
import subprocess
import sys

import pytest

from agent.template import explain as floor_explain
from solver import objects
from solver.frozen import FrozenIntercept, MANIFEST_DIR, load, load_all, path_for
from verify.groundedness import check

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAVY = ("numpy", "astropy", "hapsira", "scipy")


@pytest.fixture(scope="module")
def frozen():
    """The three committed envelopes, keyed by object key."""
    return {fi.key: fi for fi in load_all()}


# ---------------------------------------------------------------------------
# The set is complete and committed
# ---------------------------------------------------------------------------

def test_one_committed_file_per_object():
    """
    Three files, one per key. A missing file is a freeze that was not rerun
    after the solver changed, which would otherwise show up as a 500 in
    production rather than a red test here.
    """
    for key in objects.KEYS:
        assert os.path.exists(path_for(key)), (
            f"data/manifests/{key}.json is missing. "
            "Run: python data/freeze_manifests.py")
    committed = sorted(f[:-5] for f in os.listdir(MANIFEST_DIR)
                       if f.endswith(".json"))
    assert committed == sorted(objects.KEYS)


def test_a_key_outside_the_set_is_refused():
    """No free-text target survives the freeze either."""
    for bad in ["2I/Borisov", "1I", "", "Oumuamua", "../state_vectors"]:
        with pytest.raises(KeyError) as exc:
            load(bad)
        assert "free-text" in str(exc.value)


# ---------------------------------------------------------------------------
# (a) Round trip
# ---------------------------------------------------------------------------

def test_round_trip_preserves_entries_call_id_and_verification_status(frozen):
    """
    from_dict(to_dict(x)) is the identity on everything a surface reads.

    Entries are compared field by field rather than by count. A round trip that
    kept twelve entries and lost every rendering would pass a length check and
    would break the gate, which matches on renderings and nothing else.
    """
    for key, fi in frozen.items():
        again = FrozenIntercept.from_dict(fi.to_dict())

        assert again.call_id == fi.call_id
        assert again.verification_status == fi.verification_status
        assert again.verification_basis == fi.verification_basis
        assert again.transfer_basis == fi.transfer_basis
        assert again.designation == fi.designation
        assert again.manifest.producer == fi.manifest.producer
        assert again.manifest.fidelity_note == fi.manifest.fidelity_note

        assert len(again.manifest.entries) == len(fi.manifest.entries)
        for a, b in zip(again.manifest.entries, fi.manifest.entries):
            assert a.id == b.id
            assert a.canonical == b.canonical
            assert a.renderings == b.renderings
            assert a.kind == b.kind
            assert a.unit == b.unit
            assert a.frame == b.frame
            assert a.label == b.label
            assert a.value == b.value
            assert a.value_type == b.value_type
            assert a.text_value == b.text_value


def test_committed_file_is_byte_stable_through_a_round_trip(frozen):
    """
    Loading and reserializing reproduces the committed JSON exactly. A field
    the loader silently drops would otherwise be invisible until whatever reads
    it in production finds it missing.
    """
    for key, fi in frozen.items():
        with open(path_for(key)) as fh:
            on_disk = json.load(fh)
        assert fi.to_dict() == on_disk


def test_verification_status_is_not_a_manifest_entry(frozen):
    """
    It rides on the envelope, never in the universe of citable numbers.

    solver/objects.py gives the reason: a claim about the literature is not
    something the solver computed, and an entry for it would be a sentence the
    agent could quote with the solver's authority behind it.
    """
    for fi in frozen.values():
        ids = {e.id for e in fi.manifest.entries}
        assert not any("verification" in i for i in ids)
        blob = json.dumps([{"id": e.id, "label": e.label,
                            "renderings": e.renderings}
                           for e in fi.manifest.entries])
        assert "no published intercept study" not in blob


def test_oumuamua_alone_carries_the_published_validation(frozen):
    """
    The distinction the three-object count must never blur. 'Oumuamua was
    checked against Hein et al. 2019; the other two were checked against
    nothing, because there is nothing published to check them against.
    """
    assert frozen["oumuamua"].verification_status == objects.VALIDATED
    assert frozen["oumuamua"].is_validated
    assert frozen["oumuamua"].verification_basis

    for key in ("borisov", "atlas"):
        assert frozen[key].verification_status == objects.UNVALIDATED
        assert not frozen[key].is_validated
        assert "no published intercept study" in frozen[key].verification_status


# ---------------------------------------------------------------------------
# (b) The floor is grounded against every frozen manifest
# ---------------------------------------------------------------------------

def test_floor_over_each_frozen_manifest_is_grounded(frozen):
    """
    The claim the service rests on. Every number the floor prints for an object
    is a rendering the committed file permits, so the answer served with no
    credentials and no network is a gated answer and not merely a canned one.
    """
    for key, fi in frozen.items():
        text = floor_explain(fi.manifest)
        verdict = check(text, fi.manifest)
        assert verdict.grounded, (
            f"{key}: floor is ungrounded against its own frozen manifest: "
            f"{[(f.text, f.reason) for f in verdict.findings]}")
        assert verdict.checks_run


def test_floor_names_the_target_and_states_the_fidelity_limit(frozen):
    """
    Two things CLAUDE.md requires of any surface presenting these numbers: the
    reader knows which object the figures are about, and knows the model is
    patched-conic.
    """
    for key, fi in frozen.items():
        text = floor_explain(fi.manifest)
        assert fi.designation in text
        assert "patched-conic" in text.lower()


# ---------------------------------------------------------------------------
# (c) call_id scoping survives the freeze
# ---------------------------------------------------------------------------

def test_each_objects_answer_fails_the_other_two_frozen_manifests(frozen):
    """
    Six ordered pairs, all rejected.

    This is the test that stops the freeze quietly merging three calls into
    one. Borisov and 3I/ATLAS were solved at the same flight time, so their
    manifests carry the same 7305 and the same 20 and their C3 figures are the
    same order of magnitude; a plausible number from the wrong object is
    exactly the failure that would otherwise go unnoticed.
    """
    for a_key, a in frozen.items():
        text = floor_explain(a.manifest)
        for b_key, b in frozen.items():
            if a_key == b_key:
                continue
            verdict = check(text, b.manifest)
            assert not verdict.grounded, (
                f"{a_key}'s answer passed the gate against {b_key}'s frozen "
                "manifest; the manifests are not scoping the call")


def test_the_three_call_ids_are_distinct_and_pinned(frozen):
    """
    Distinct, so scoping has something to key on, and identical to what is on
    disk, so an answer checked in CI is checked against the same call the
    service serves.
    """
    call_ids = [fi.call_id for fi in frozen.values()]
    assert len(set(call_ids)) == 3
    for key, fi in frozen.items():
        with open(path_for(key)) as fh:
            assert json.load(fh)["manifest"]["call_id"] == fi.call_id


# ---------------------------------------------------------------------------
# (d) Import weight
# ---------------------------------------------------------------------------

SUBPROCESS_PROBE = """
import sys, json
from solver.frozen import load_all
from agent.template import explain
from verify.groundedness import check

grounded = []
for fi in load_all():
    grounded.append(check(explain(fi.manifest), fi.manifest).grounded)

heavy = sorted({m.split('.')[0] for m in sys.modules
                if m.split('.')[0] in %r})
print(json.dumps({"heavy": heavy, "grounded": grounded,
                  "n_modules": len(sys.modules)}))
""" % (HEAVY,)


def test_serving_a_frozen_manifest_imports_no_scientific_stack():
    """
    The guard that keeps the deployed process small enough to be free.

    Run in a subprocess on purpose: this suite imports the solver, so by the
    time any test runs numpy is already in sys.modules and an in-process check
    would be answering a different question. The probe does the real work,
    loading all three envelopes and running the floor and the gate over each,
    so it fails if serving needs the stack rather than if merely importing does.
    """
    proc = subprocess.run(
        [sys.executable, "-c", SUBPROCESS_PROBE],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"probe failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")

    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["grounded"] == [True, True, True], (
        "the probe did not actually serve all three; an import check over work "
        "that did not happen proves nothing")
    assert out["heavy"] == [], (
        f"serving pulled in {out['heavy']}. The deployed web process must "
        "import none of numpy, astropy, hapsira or scipy; something in "
        "solver.frozen, solver.manifest, agent.template or verify.groundedness "
        "has grown a dependency on the solver stack.")
