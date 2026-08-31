"""
tests/test_intercept.py — the three committed objects, their manifests, and the
floor's answer for each.

What this module is for is the claim the README makes: that HITS computes an
intercept for all three interstellar objects humanity has found. That sentence
is only true if three objects each produce a grounded answer, so the test that
each does is the test that keeps the sentence honest.

The offline guarantee holds here as everywhere: every number comes from
committed state vectors and no Horizons call is made.
"""

import pytest

from agent.template import explain_intercept
from solver import objects
from solver.intercept import intercept
from verify.groundedness import check


@pytest.fixture(scope="module")
def intercepts(state_vectors):
    """One InterceptResult per committed object, keyed by object key."""
    return {key: intercept(key, state_vectors) for key in objects.KEYS}


# ---------------------------------------------------------------------------
# The committed set
# ---------------------------------------------------------------------------

def test_three_objects_and_no_more():
    """
    Three, because three is how many have been found. An unexplained fourth
    entry would make the README's count wrong without anything else failing.
    """
    assert objects.KEYS == ("oumuamua", "borisov", "atlas")
    assert set(objects.OBJECTS) == set(objects.KEYS)
    assert [o.designation for o in objects.all_objects()] == [
        "1I/'Oumuamua", "2I/Borisov", "3I/ATLAS"]


def test_no_free_text_target():
    """
    The target is a key from a committed set, never a designation a user typed.
    A free-text field would need a live Horizons call at request time, which
    breaks the offline guarantee the whole validation rests on.
    """
    for bad in ["2I/Borisov", "1I", "C/2019 Q4", "", "Oumuamua", "borisov "]:
        with pytest.raises(KeyError) as exc:
            objects.get(bad)
        assert "free-text" in str(exc.value)


def test_solve_reads_the_states_the_object_declares(state_vectors, intercepts):
    """The flight time an object declares is the gap between its two states."""
    for key, ir in intercepts.items():
        obj = objects.get(key)
        gap = (state_vectors[obj.target_key].epoch_tdb_jd
               - state_vectors[obj.earth_key].epoch_tdb_jd)
        assert gap == pytest.approx(obj.tof_days, abs=1e-6)
        assert ir.result.tof_days == pytest.approx(obj.tof_days, abs=1e-6)


# ---------------------------------------------------------------------------
# Verification status
# ---------------------------------------------------------------------------

def test_verification_status_is_a_field_not_prose(intercepts):
    """
    Present on the object, on the result, and in the serialized form. A judges
    page renders fields; a status that lives only in a document does not reach
    it.
    """
    for key, ir in intercepts.items():
        assert ir.verification_status
        assert ir.verification_status == objects.get(key).verification_status
        assert ir.to_dict()["verification_status"] == ir.verification_status


def test_only_oumuamua_claims_validation(intercepts):
    """
    The honesty gate on the whole three-object claim. "Validated against
    published figures" attaches to the one object with published figures behind
    it, and the other two say plainly that no study exists.
    """
    assert intercepts["oumuamua"].verification_status == objects.VALIDATED
    assert intercepts["oumuamua"].obj.is_validated
    assert "Hein et al. 2019" in intercepts["oumuamua"].verification_basis

    for key in ("borisov", "atlas"):
        ir = intercepts[key]
        assert ir.verification_status == objects.UNVALIDATED
        assert not ir.obj.is_validated
        assert "no published intercept study" in ir.verification_status
        assert "validated" not in ir.verification_status
        assert ir.verification_basis == ""


def test_status_is_not_a_manifest_entry(intercepts):
    """
    A provenance claim is not a computed number. If it were an entry the agent
    could quote it with the solver's authority behind it.
    """
    for ir in intercepts.values():
        for e in ir.manifest.entries:
            assert "no published intercept study" not in e.label
            assert "validated" not in e.label.lower()


# ---------------------------------------------------------------------------
# The manifests
# ---------------------------------------------------------------------------

def test_manifests_are_solve_shaped_with_distinct_call_ids(intercepts):
    call_ids = [ir.call_id for ir in intercepts.values()]
    assert len(set(call_ids)) == len(call_ids)
    for ir in intercepts.values():
        assert ir.manifest.producer == "solve"
        assert ir.manifest.inputs["object_key"] == ir.obj.key


# ---------------------------------------------------------------------------
# The floor, gated
# ---------------------------------------------------------------------------

def test_floor_answers_every_object_and_is_grounded(intercepts):
    """
    Three objects, three grounded answers. This is the test the README's count
    depends on.
    """
    for key, ir in intercepts.items():
        text = explain_intercept(ir.manifest)
        verdict = check(text, ir.manifest)
        assert verdict.grounded, (
            f"{key}: floor rejected by its own gate: "
            f"{[(f.text, f.reason) for f in verdict.findings]}")


# The sentences that do the honest work, which have to be there whatever the
# departure energy turns out to be. Kept as data so the assertion below names
# what is missing rather than reporting that a long string was absent.
FRAMING = (
    "That such a trajectory exists is geometry",
    "what separates one departure from another is what it costs to fly",
    "the input to a feasibility judgement rather than the judgement itself",
    "this answer reads the same way whatever the size of that figure",
    "come back in identical sentences",
    "Nothing above should be read as HITS having found the mission flyable",
)


def test_framing_carries_to_every_scale(intercepts):
    """
    The question this test exists to answer: does the honest framing survive a
    departure energy several times 'Oumuamua's?

    It has to, because the template is scale-blind by construction and a reader
    who cannot tell a cheap transfer from a ruinous one by the numbers has only
    the prose to go on. If the qualifiers appeared for the cheap case and the
    expensive case read as a finding, the expensive case is the one a judge
    would misread.
    """
    for key, ir in intercepts.items():
        text = explain_intercept(ir.manifest)
        for sentence in FRAMING:
            assert sentence in text, f"{key}: framing missing: {sentence!r}"


def test_the_only_difference_between_objects_is_the_numbers(intercepts):
    """
    Strip every manifest rendering and the prose left over is the same prose.

    This is the scale-blindness claim stated as an equality rather than as an
    adjective. It is also why the closing limit says out loud that the wording
    does not change with the figure: the wording provably does not.
    """
    skeletons = {}
    for key, ir in intercepts.items():
        text = explain_intercept(ir.manifest)
        for e in sorted(ir.manifest.entries,
                        key=lambda e: len(e.canonical), reverse=True):
            text = text.replace(e.canonical, "<N>")
        # Singular and plural nouns follow the rendering, not the framing.
        text = text.replace("<N> day,", "<N> days,").replace(
            "<N> year.", "<N> years.")
        skeletons[key] = text

    distinct = set(skeletons.values())
    assert len(distinct) == 1, (
        "the three answers do not share one skeleton, so the framing is not "
        "the same at every scale:\n" + "\n\n".join(
            f"--- {k} ---\n{v}" for k, v in skeletons.items()))


def test_floor_states_no_feasibility_verdict(intercepts):
    """
    HITS has no launch-vehicle model, so an answer that said "feasible" or
    "impossible" would be a judgement the solver never made. 3I/ATLAS is the
    case that tempts it: the departure energy is the largest of the three.
    """
    for ir in intercepts.values():
        text = explain_intercept(ir.manifest).lower()
        for verdict_word in ("infeasible", "impossible", "unachievable",
                             "is feasible", "not feasible"):
            assert verdict_word not in text


def test_an_answer_does_not_ground_against_another_object(intercepts):
    """
    What call_id scoping is for. Borisov and 3I/ATLAS fly the same 7305 days
    and their departure energies are the same order of magnitude, so their
    explanations read as though they could be swapped. The gate is what makes
    sure they cannot be.
    """
    for key, ir in intercepts.items():
        text = explain_intercept(ir.manifest)
        for other_key, other in intercepts.items():
            if other_key == key:
                continue
            verdict = check(text, other.manifest)
            assert not verdict.grounded, (
                f"{key}'s answer passed the gate against {other_key}'s "
                "manifest; the two calls are not isolated")
