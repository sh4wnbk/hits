"""
tests/test_manifest.py — the manifest contract, docs/MANIFEST.md.

Two things are proved here, and they are the two the gate depends on.

Pinning. The rendering ladder is the whole reason the gate can be a pure
membership test, so the four worked ladders in docs/MANIFEST.md are
regenerated exactly. If they cannot be, the policy is not pinned and every
downstream guarantee is resting on an unstated rounding convention.

Completeness. Every float the public surface produces has a manifest entry,
checked by reflection over the dataclasses rather than by a hand-maintained
list. A number cannot be dropped by oversight, only by editing this test.
"""

import dataclasses
import json
import os

import pytest

from solver.fetch import load_state_vectors
from solver.manifest import (
    Manifest, ManifestEntry, build_renderings, date_renderings,
    from_validation_results, from_solve_result, UNITS, FRAMES, KINDS,
)
from solver.solve import SolveResult, solve
from solver.validate import (
    validate, FrameGateResult, C3Result, ArrivalResult, ValidationResults,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "manifests")
VALIDATE_FIXTURE = os.path.join(FIXTURE_DIR, "validate_full.json")


@pytest.fixture(scope="module")
def results(state_vectors):
    return validate(state_vectors, verbose=False)


@pytest.fixture(scope="module")
def manifest(results):
    return results.manifest


# ---------------------------------------------------------------------------
# 1. The ladder, pinned
# ---------------------------------------------------------------------------

# docs/MANIFEST.md, "The four pinned ladders". These are the contract.
PINNED_LADDERS = [
    (714.36, 2, ["714.36", "714.4", "714"]),
    (1.62, 2, ["1.62", "1.6"]),
    (26.28614, 5, ["26.28614", "26.2861", "26.286", "26.29", "26.3"]),
    (0.64166, 5, ["0.64166", "0.6417", "0.642", "0.64"]),
    # The sub-0.1 regime, pinned because it is where the two-significant-digits
    # clause was least obviously right. Leading zeros are not significant, so
    # the floor scales with magnitude on its own and needs no special case:
    # 0.044 is two significant figures with a fraction and survives, 0.04 is
    # one and does not. "The frame gate agrees to within 0.044 km/s" is the
    # truest sentence in the validation and it has to stay sayable.
    (0.04386, 5, ["0.04386", "0.0439", "0.044"]),
    (0.00186, 5, ["0.00186", "0.0019"]),
]


@pytest.mark.parametrize("value,precision,expected", PINNED_LADDERS)
def test_pinned_ladders(value, precision, expected):
    """The four ladders docs/MANIFEST.md commits to, regenerated exactly."""
    assert build_renderings(value, precision) == expected


def test_ladder_excludes_the_near_misses_it_is_meant_to():
    """
    The exclusions carry the guarantee, so they are asserted directly rather
    than left implied by the ladders above.
    """
    # A plausible rounding of a real number is not a rendering of it.
    assert "710" not in build_renderings(714.36, 2)
    # Two significant digits with no fractional part is too coarse to quote.
    assert "26" not in build_renderings(26.28614, 5)
    # HITS's computed 0.64166 km/s must not be quotable as Lyra's published 0.6.
    assert "0.6" not in build_renderings(0.64166, 5)
    # Precision inflation: a value held at precision 5 that lands on 0.044 must
    # not offer a five-decimal rendering claiming digits it does not have.
    assert build_renderings(0.044, 5) == ["0.044"]
    assert "0.04400" not in build_renderings(0.044, 5)
    # Sub-0.1 values keep the rung that reads naturally and drop the one that
    # has thrown away a significant figure.
    assert "0.044" in build_renderings(0.04386, 5)
    assert "0.04" not in build_renderings(0.04386, 5)
    assert "0.002" not in build_renderings(0.00186, 5)
    # Nor may a two-decimal value offer a third decimal.
    assert "1.620" not in build_renderings(1.62, 2)


def test_integral_physical_quantities_render_both_ways():
    """
    "15 years" and "15.0 years" are equally correct prose, and rejecting the
    second would be a false positive on writing that is not wrong about
    anything. Counts and calendar years are excluded from this.
    """
    from solver.manifest import entry
    yrs = entry("t.yr", "flight time", 15.0, "yr", "derived", precision=2)
    assert yrs.renderings == ["15", "15.0"]
    count = entry("t.n", "departures", 391.0, "1", "count", precision=0)
    assert count.renderings == ["391"]


# ---------------------------------------------------------------------------
# 2. Completeness, by reflection
# ---------------------------------------------------------------------------

# Fields that are deliberately not citable, with the reason. Anything else that
# is a float must appear in the manifest.
NOT_CITABLE = {
    # Vectors and arrays, not scalars an explanation quotes.
    "v_depart_helio_km_s", "v_arrive_helio_km_s",
    # Booleans and prose carried alongside the numbers.
    "passed", "c3_2027_passed", "c3_floor_passed",
    "citation", "c3_2027_citation", "c3_floor_citation", "formula",
    "fidelity_note", "retrieval_date", "sample_label",
    "c3_floor_edge_type", "c3_floor_gap_attribution",
}


def _numeric_fields(obj):
    out = {}
    for f in dataclasses.fields(obj):
        if f.name in NOT_CITABLE:
            continue
        val = getattr(obj, f.name)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            out[f.name] = float(val)
    return out


def test_every_float_of_every_public_result_is_in_the_manifest(results, manifest):
    """
    Reflection over the public dataclasses. The check is on the VALUE being
    quotable, not on an id naming convention, because the manifest is allowed
    to restructure ids as long as no number goes missing.
    """
    index = manifest.index()
    missing = []
    for obj, name in (
        (results.frame_gate, "FrameGateResult"),
        (results.c3, "C3Result"),
        (results.arrival_a, "ArrivalResult(A)"),
        (results.arrival_b, "ArrivalResult(B)"),
    ):
        for fname, val in _numeric_fields(obj).items():
            # Keyed on the declared type, not on whether `value` happens to
            # be None. Those read the same and are not the same: this skips
            # entries that are dates, and still fails on a number that arrived
            # without a value, which is the failure this test exists to catch.
            found = any(
                e.is_number and abs(e.value - val) < 10 ** (-e.precision) / 2
                for entries in index.values() for e in entries
            )
            if not found:
                missing.append(f"{name}.{fname} = {val}")
    assert not missing, (
        "public result fields with no manifest entry, so an explanation stating "
        "them correctly would be rejected:\n  " + "\n  ".join(missing)
    )


DECLARED_DERIVED = [
    "validate.c3.y2027.tof_years",
    "validate.c3.floor.tof_years",
    "validate.c3.y2027.tolerance_pct",
    "validate.c3.floor.tolerance_pct",
    "validate.c3.y2027.tolerance_abs",
    "validate.c3.floor.tolerance_abs",
    "validate.c3.y2027.departure.iso",
    "validate.c3.y2027.departure.year",
    "validate.c3.floor.departure.iso",
    "validate.c3.floor.departure.year",
    "validate.c3.grid.n_departures",
    "validate.c3.grid.n_durations",
    "validate.c3.grid.n_cells",
    "validate.c3.grid.n_solved",
    "validate.c3.grid.duration_min_years",
    "validate.c3.grid.duration_max_years",
    "validate.c3.grid.launch_window_start.year",
    "validate.c3.grid.launch_window_end.year",
    "validate.arrival_a.tof_years",
    "validate.arrival_b.tof_years",
    "validate.arrival_a.launch.iso",
    "validate.arrival_a.arrival.year",
    "validate.arrival_b.arrival.year",
    "validate.arrival_a.published_tof_years",
    "validate.arrival_b.published_tof_years",
    "validate.arrival_a.published_encounter_au",
    "validate.arrival_b.published_encounter_au",
    "source.lyra.publication_year",
    "source.horizons.retrieval_year",
]


def test_declared_derived_entries_all_present(manifest):
    """
    Derived numbers are not dataclass fields, so reflection cannot find them.
    They are declared here instead, and docs/MANIFEST.md lists the same set.
    """
    ids = {e.id for e in manifest.entries}
    missing = [i for i in DECLARED_DERIVED if i not in ids]
    assert not missing, f"declared derived entries missing: {missing}"


# The complete set of entries permitted to be non-numeric. Declared here so a
# new one has to be added deliberately.
DATE_TYPED_IDS = {
    "validate.c3.y2027.departure.iso",
    "validate.c3.floor.departure.iso",
    "validate.c3.grid.launch_window_start.iso",
    "validate.c3.grid.launch_window_end.iso",
    "validate.arrival_a.launch.iso",
    "validate.arrival_a.arrival.iso",
    "validate.arrival_b.launch.iso",
    "validate.arrival_b.arrival.iso",
    "source.horizons.retrieval_date",
}


def test_only_declared_date_entries_are_non_numeric(manifest):
    """
    The set of entries without a numeric value is exactly the declared date set.

    Without this, the completeness guard's exemption has no boundary: an entry
    could arrive non-numeric, not be a date, and go unremarked, which is the
    same class of hole as a field quietly filled with a placeholder. A new
    date-typed entry has to be added to DATE_TYPED_IDS on purpose.
    """
    non_numeric = {e.id for e in manifest.entries if not e.is_number}
    assert non_numeric == DATE_TYPED_IDS, (
        f"unexpected non-numeric entries: {sorted(non_numeric - DATE_TYPED_IDS)}; "
        f"declared but now numeric or absent: {sorted(DATE_TYPED_IDS - non_numeric)}")
    assert all(e.value is None for e in manifest.entries if not e.is_number)
    assert all(e.value is not None for e in manifest.entries if e.is_number)


def test_a_number_that_lost_its_value_is_rejected_at_construction():
    """
    The failure the type split exists to catch, asserted directly rather than
    left to the completeness test's search direction.
    """
    from solver.manifest import entry
    with pytest.raises(AssertionError, match="declared a number but carries no value"):
        entry("t.lost", "a computed float that went missing", None, "km/s",
              "computed", precision=5, renderings=["0.5"], text_value="oops")
    with pytest.raises(AssertionError, match="declared a date but carries a numeric value"):
        entry("t.placeholder", "a date with an invented year", 2018.0, "1",
              "epoch", precision=0, renderings=["2018-06-04"],
              text_value="2018-06-04", value_type="date")


def test_date_entries_carry_their_date_and_no_invented_number(manifest):
    """
    A calendar date has no float that means anything. Filling `value` with the
    year to satisfy the type made the entry look, in any view that withholds
    renderings, like an ISO field that had silently lost its month and day.
    The date is the content, so it lives in `text_value`, and `value` is None.
    """
    dated = [e for e in manifest.entries if e.value_type == "date"]
    assert dated
    for e in dated:
        assert e.value is None, f"{e.id} carries an invented numeric value {e.value}"
        assert e.text_value, f"{e.id} has no text_value"
        assert e.renderings == date_renderings(e.text_value), (
            f"{e.id}: a date renders as the closed set and nothing else")
        assert e.renderings[0] == e.text_value, (
            f"{e.id}: the ISO form is canonical; the human form is the "
            "alternate, not the other way round")
        assert len(e.renderings) == 2, (
            f"{e.id}: the set of date forms is closed at two. An open set of "
            "date spellings is a fuzzy match wearing a table's clothes")
        assert len(e.text_value) == 10 and e.text_value[4] == "-", (
            f"{e.id}: {e.text_value!r} is not a full ISO date")


def test_full_dates_are_groundable_not_just_years(manifest):
    """
    The manifest grounds a full calendar date, not only its year. Asserted
    directly because a redacted view that hides renderings makes this look
    otherwise, and the question is worth settling in a test rather than in a
    reading of one.
    """
    index = manifest.index()
    for date in ("2018-06-04", "2027-06-21", "2017-06-07", "2037-06-07",
                 "2018-01-01", "2032-12-13", "2026-08-27"):
        assert date in index, f"{date} is not groundable"
    # And the year alone remains separately groundable, with its own unit, so a
    # fabricated quantity wearing a year's clothes still fails the unit check.
    for year in ("2018", "2027", "2017", "2037", "2032", "2026", "2019"):
        assert year in index
        assert any(e.unit == "calendar_year" for e in index[year])


def test_entry_vocabularies_are_closed(manifest):
    for e in manifest.entries:
        assert e.unit in UNITS
        assert e.frame in FRAMES
        assert e.kind in KINDS
        assert e.renderings
        if e.kind == "published":
            assert e.citation, f"{e.id} is published with no citation"


def test_published_figures_are_never_re_rounded(manifest):
    """
    A source figure is quotable exactly as the source prints it. Lyra's 26.33
    must not become 26.3, because re-rounding someone else's number
    misrepresents the precision they reported.
    """
    for e in manifest.entries:
        if e.kind == "published":
            assert len(e.renderings) <= 2, (
                f"{e.id} offers {e.renderings}; a published figure gets its "
                "source form, not a ladder"
            )
    assert manifest.by_id("validate.frame_gate.published").renderings == ["26.33"]
    assert manifest.by_id("validate.c3.floor.published").renderings == ["703"]
    assert manifest.by_id("validate.arrival_b.published").renderings == ["0.6"]


# Renderings claimed by more than one entry, each reviewed once and recorded
# with why it is harmless. A collision is not a defect in itself: two entries
# can legitimately be equal, or can coincide at a coarse rung. It is only a
# defect if a claim about one entry could be grounded by another entry's ladder
# while being false of the first. New collisions fail this test until someone
# has looked at them and written the reason down.
REVIEWED_COLLISIONS = {
    "0.2": "both C3 tolerance fractions are 20 percent; equal values",
    "20": "C3 tolerance in percent against Sample B's 20-year flight time; "
          "different units, so the gate's unit check separates them",
    "30": "the floor's 30-year flight time is the grid's longest duration; "
          "equal values",
    "30.0": "as above",
    "20.0": "Sample B's computed 20-year flight time equals Lyra's published "
            "20.0 years exactly; equal values",
    "2018": "the floor departs in the grid's first launch year and Sample A "
            "arrives in it; equal values",
    "10166": "every grid cell solved, so n_cells equals n_solved; equal values",
    "2457912.0": "samples A and B share one launch instant (PROVENANCE.md)",
    "2017-06-07": "as above",
    "June 7, 2017": "as above, in the human rendering of the same shared "
                    "launch date. The collision is the ISO one restated, not a "
                    "new ambiguity: both forms name one instant",
    "2017": "as above",
    "0.64": "Sample B's eq.4 asymptotic velocity (0.64166) and its local "
            "encounter velocity (0.64351) coincide at two significant digits. "
            "They are different quantities in the same unit and frame, so the "
            "gate cannot tell which one a bare '0.64 km/s' refers to. It does "
            "not need to: the statement is true of both. This is a stated "
            "limit of the coarse rungs, not a way to smuggle a false number in, "
            "and PROVENANCE.md already records that the two nearly coincide at "
            "Sample B's distance.",
    "1": "Sample A's computed flight time in years rounds to Lyra's published "
         "1.0 year at this precision; equal values",
    "1.0": "as above",
}


def test_collisions_are_all_reviewed(manifest):
    """
    Every rendering claimed by more than one entry has been looked at and the
    reason recorded. The inventory is the point: collisions accumulating
    unnoticed is how a gate quietly stops discriminating.
    """
    found = manifest.collisions()
    unreviewed = {r: ids for r, ids in found.items() if r not in REVIEWED_COLLISIONS}
    assert not unreviewed, (
        "new manifest rendering collisions, each needs a reviewed reason in "
        f"REVIEWED_COLLISIONS: {unreviewed}")
    stale = [r for r in REVIEWED_COLLISIONS if r not in found]
    assert not stale, f"reviewed collisions that no longer occur, drop them: {stale}"


def test_collisions_across_units_are_separable(manifest):
    """
    The collision that matters most is "20": a 20 percent tolerance and a
    20-year flight time. The gate separates them on unit, so that separation is
    asserted directly rather than left to the inventory above.
    """
    entries = manifest.index()["20"]
    assert {e.unit for e in entries} == {"%", "yr"}


# ---------------------------------------------------------------------------
# 3. Frozen fixtures
# ---------------------------------------------------------------------------

def test_frozen_fixture_matches_freshly_emitted_manifest(manifest):
    """
    The adversarial corpus is written against a committed manifest fixture. If
    the solver's numbers move, the corpus is judging against a manifest that no
    longer exists, so this test is what keeps the corpus honest.

    Regenerate with:  python -m solver.manifest --freeze
    """
    assert os.path.exists(VALIDATE_FIXTURE), (
        "manifest fixture missing; run: python -m solver.manifest --freeze")
    with open(VALIDATE_FIXTURE) as fh:
        frozen = Manifest.from_json(fh.read())

    fresh = {e.id: (e.value, tuple(e.renderings), e.unit, e.frame, e.kind)
             for e in manifest.entries}
    old = {e.id: (e.value, tuple(e.renderings), e.unit, e.frame, e.kind)
           for e in frozen.entries}

    assert set(fresh) == set(old), (
        f"entry ids drifted.\n  added: {sorted(set(fresh) - set(old))}\n"
        f"  removed: {sorted(set(old) - set(fresh))}")
    drifted = {k: (old[k], fresh[k]) for k in fresh if fresh[k] != old[k]}
    assert not drifted, f"manifest values drifted from the frozen fixture: {drifted}"


def test_solve_manifest_emits(state_vectors):
    """The single-transfer manifest, so /solve is grounded the same way."""
    r = solve(state_vectors["earth_sample_ab_launch"],
              state_vectors["oumuamua_sample_a_arrival"], 365.0)
    m = from_solve_result(r)
    assert m.producer == "solve"
    ids = {e.id for e in m.entries}
    for required in ("solve.c3", "solve.v_inf2", "solve.tof_days",
                     "solve.arrival.year"):
        assert required in ids
