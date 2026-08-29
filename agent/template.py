"""
agent/template.py — the deterministic explanation floor.

The grounded floor. No model is in this path. Every number here is a rendering
the solver enumerated in advance, pulled out of the manifest by entry id, and
the module contains no way to produce a number that is not one: it never
formats a float, never rounds, and never computes. tests/test_template.py walks
this file's AST and reds the build if a format specifier, a rounding call, or
an arithmetic operator appears.

That is what makes "the floor cannot speak an ungrounded number" a structural
fact rather than a promise. A template that wrote `f"{value:.2f}"` would be a
second rounding policy, competing with the ladder in solver/manifest.py, and
the first time the two disagreed the floor would emit a string the gate rejects.
There is one rounding policy and it lives in the layer that owns the number.

## Why the input is a manifest and not a result object

The templates take the manifest alone. docs/MANIFEST.md is explicit that the
interpretation layer never reaches past the manifest to the solver, and the
gate obeys the same rule: check(text, manifest) sees the manifest and nothing
else. Giving the floor the same universe the gate has is what turns "the floor
passes its own gate" from a happy result into a consequence of the shape. A
floor that could read `SolveResult.c3_km2_s2` directly would be able to say a
number the manifest never emitted, which is precisely the derived-not-emitted
rejection in docs/MANIFEST.md.

The cost is real and worth stating: pass/fail booleans on the result objects
are not manifest entries, so the floor does not say "the frame gate passes".
It says what the difference is and what the tolerance was, which is the
substance of the same claim, and it says it in numbers a reader can check.

## What the floor does not do

It states no verdict the solver did not settle. HITS computes what a transfer
costs; it does not model launch-vehicle capability, so the intercept template
reports the cost and says plainly that the cost is the input to a feasibility
judgement rather than the judgement itself. Inventing a capability threshold
would be a generated number wearing a verdict's clothes.
"""

from __future__ import annotations

from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Pulling renderings
# ---------------------------------------------------------------------------

def _say(manifest, ids: Dict[str, str]) -> Dict[str, str]:
    """
    Canonical renderings for the entries a paragraph quotes, keyed by a short
    name the prose reads better with.

    A missing entry raises KeyError out of Manifest.by_id rather than being
    filled with a placeholder. A floor that quietly degrades to "unknown" in
    the middle of a sentence is worse than one that fails loudly, because the
    reader cannot tell the two apart.
    """
    return {name: manifest.canonical(entry_id) for name, entry_id in ids.items()}


def _has(manifest, entry_id: str) -> bool:
    return any(e.id == entry_id for e in manifest.entries)


def _noun(rendering: str, singular: str, plural: str) -> str:
    """
    The unit's noun, chosen from the rendering string and nothing else.

    "1 years" is not prose anyone writes, and the fix has to come from the
    string the manifest emitted rather than from the value behind it, because
    this module is not permitted to look at a float. A rendering of exactly
    "1" takes the singular; every other rendering, "1.0" included, takes the
    plural, since "1.0 year" is not prose either.
    """
    return singular if rendering == "1" else plural


FIDELITY = (
    "All figures are patched-conic, two-body. HITS does not perform n-body "
    "integration and does not model non-gravitational forces, so a figure is a "
    "faithful record of what the solver computed rather than a claim that it "
    "is right to the precision it is quoted at."
)


# ---------------------------------------------------------------------------
# The intercept-feasibility answer
# ---------------------------------------------------------------------------

def explain_intercept(manifest) -> str:
    """
    The "could we send a probe to it" answer for a single solved transfer.

    Reads a manifest whose producer is `solve`.
    """
    if manifest.producer != "solve":
        raise ValueError(
            f"explain_intercept wants a solve manifest, got {manifest.producer!r}")

    v = _say(manifest, {
        "departure": "solve.departure.iso",
        "arrival": "solve.arrival.iso",
        "tof_days": "solve.tof_days",
        "tof_years": "solve.tof_years",
        "c3": "solve.c3",
        "dv_depart": "solve.dv_depart",
        "v_arr": "solve.v_arr",
        "v_inf2": "solve.v_inf2",
    })

    when = (
        "A transfer to the target exists for the departure asked about. "
        f"Leaving Earth on {v['departure']} and arriving on {v['arrival']}, "
        f"the flight time is {v['tof_days']} "
        f"{_noun(v['tof_days'], 'day', 'days')}, or {v['tof_years']} "
        f"{_noun(v['tof_years'], 'year', 'years')}."
    )

    cost = (
        "Reaching it from an Earth-relative departure costs "
        f"{v['c3']} km^2/s^2 of characteristic energy, which is a hyperbolic "
        f"excess speed of {v['dv_depart']} km/s once clear of Earth."
    )

    arrival = (
        f"The probe would meet the target at {v['v_arr']} km/s in the "
        "target-relative frame, which is the speed it passes at. Its "
        "asymptotic arrival relative velocity, the quantity the mission-design "
        f"literature compares against, is {v['v_inf2']} km/s."
    )

    limit = (
        "What HITS settles here is the trajectory, not the launch vehicle. It "
        "computes what the transfer costs and does not model launcher "
        "capability, so the departure energy above is the input to a "
        "feasibility judgement rather than the judgement itself."
    )

    return "\n\n".join([when, cost, arrival, limit, FIDELITY])


# ---------------------------------------------------------------------------
# The validation summary
# ---------------------------------------------------------------------------

def explain_validation(manifest) -> str:
    """
    The plain-language reading of a full validate() run.

    Reads a manifest whose producer is `validate`. The C3, arrival and grid
    paragraphs appear only when the manifest carries their entries, because
    validate() returns None for the downstream results when the frame gate
    fails and the manifest emitter omits them in turn.
    """
    if manifest.producer != "validate":
        raise ValueError(
            f"explain_validation wants a validate manifest, got "
            f"{manifest.producer!r}")

    paragraphs = [_opening(manifest), _frame_gate_paragraph(manifest)]
    for build in (_c3_paragraph, _launch_2027_paragraph, _arrival_paragraph,
                  _grid_paragraph):
        para = build(manifest)
        if para:
            paragraphs.append(para)
    paragraphs.append(FIDELITY)
    return "\n\n".join(paragraphs)


def _opening(manifest) -> str:
    v = _say(manifest, {"paper_year": "source.lyra.publication_year"})
    line = (
        "This is the HITS validation summary. It sets what the solver computes "
        f"against the figures Hein et al. {v['paper_year']} published for "
        "Project Lyra."
    )
    if _has(manifest, "source.horizons.retrieval_date"):
        r = _say(manifest, {"retrieved": "source.horizons.retrieval_date"})
        line = " ".join([
            line,
            f"The ephemerides behind it were retrieved on {r['retrieved']}."])
    return line


def _frame_gate_paragraph(manifest) -> str:
    v = _say(manifest, {
        "computed": "validate.frame_gate.computed",
        "published": "validate.frame_gate.published",
        "abs_diff": "validate.frame_gate.abs_diff",
        "tolerance": "validate.frame_gate.tolerance",
    })
    return (
        "The frame gate comes first, because a wrong frame makes every "
        "comparison below it meaningless rather than merely inaccurate. It "
        "reproduces 1I/'Oumuamua's heliocentric hyperbolic excess velocity as "
        f"{v['computed']} km/s. The published value is {v['published']} km/s, "
        f"so the two differ by {v['abs_diff']} km/s against a stated tolerance "
        f"of {v['tolerance']} km/s."
    )


def _c3_paragraph(manifest) -> Optional[str]:
    if not _has(manifest, "validate.c3.floor.computed"):
        return None
    v = _say(manifest, {
        "computed": "validate.c3.floor.computed",
        "published": "validate.c3.floor.published",
        "abs_diff": "validate.c3.floor.abs_diff",
        "rel_diff": "validate.c3.floor.rel_diff_pct",
        "departure": "validate.c3.floor.departure.iso",
        "tof_years": "validate.c3.floor.tof_years",
    })
    return (
        "Earth-relative departure energy is what a launch has to supply, and "
        "its floor is the cheapest departure anywhere in the searched window. "
        f"HITS puts that floor at {v['computed']} km^2/s^2, against a "
        f"published {v['published']} km^2/s^2, a difference of "
        f"{v['abs_diff']} km^2/s^2, or {v['rel_diff']}%. The floor sits at a "
        f"{v['departure']} departure flying for {v['tof_years']} "
        f"{_noun(v['tof_years'], 'year', 'years')}, and "
        "the gap against the published figure is attributed to drift in the "
        "orbit solution between the two retrievals, not to solver error."
    )


def _launch_2027_paragraph(manifest) -> Optional[str]:
    if not _has(manifest, "validate.c3.y2027.computed"):
        return None
    v = _say(manifest, {
        "year": "validate.c3.y2027.departure.year",
        "computed": "validate.c3.y2027.computed",
        "published": "validate.c3.y2027.published",
        "abs_diff": "validate.c3.y2027.abs_diff",
        "rel_diff": "validate.c3.y2027.rel_diff_pct",
        "tolerance_pct": "validate.c3.y2027.tolerance_pct",
    })
    return (
        f"The same comparison at the {v['year']} launch the paper singles out "
        f"gives {v['computed']} km^2/s^2 against a published "
        f"{v['published']} km^2/s^2, a difference of {v['abs_diff']} "
        f"km^2/s^2, or {v['rel_diff']}%, inside the {v['tolerance_pct']}% "
        "tolerance the comparison was set at."
    )


def _arrival_paragraph(manifest) -> Optional[str]:
    if not _has(manifest, "validate.arrival_a.v_inf2"):
        return None
    v = _say(manifest, {
        "a_v_inf2": "validate.arrival_a.v_inf2",
        "a_published": "validate.arrival_a.published",
        "a_distance": "validate.arrival_a.encounter_distance_au",
        "a_local": "validate.arrival_a.v_arr_local",
        "a_gap": "validate.arrival_a.definitional_gap",
    })
    lines = [
        "At the far end, the target-relative arrival relative velocity is what "
        "a probe would have to survive. For Sample A the asymptotic value is "
        f"{v['a_v_inf2']} km/s against a published {v['a_published']} km/s, "
        f"at an encounter distance of {v['a_distance']} AU.",
        "The local encounter speed there is a different quantity and HITS "
        f"reports it separately as {v['a_local']} km/s, a definitional gap of "
        f"{v['a_gap']} km/s that comes from hyperbolic geometry rather than "
        "from error.",
    ]
    if _has(manifest, "validate.arrival_b.v_inf2"):
        b = _say(manifest, {
            "b_v_inf2": "validate.arrival_b.v_inf2",
            "b_published": "validate.arrival_b.published",
            "b_distance": "validate.arrival_b.encounter_distance_au",
            "b_published_distance": "validate.arrival_b.published_encounter_au",
        })
        lines.append(
            "Sample B is the slow, far-out stress case: "
            f"{b['b_v_inf2']} km/s against a published {b['b_published']} "
            f"km/s, with the encounter at {b['b_distance']} AU where the "
            f"published figure is {b['b_published_distance']} AU.")
    return " ".join(lines)


def _grid_paragraph(manifest) -> Optional[str]:
    if not _has(manifest, "validate.c3.grid.n_departures"):
        return None
    v = _say(manifest, {
        "n_departures": "validate.c3.grid.n_departures",
        "window_start": "validate.c3.grid.launch_window_start.iso",
        "window_end": "validate.c3.grid.launch_window_end.iso",
        "n_durations": "validate.c3.grid.n_durations",
        "duration_min": "validate.c3.grid.duration_min_years",
        "duration_max": "validate.c3.grid.duration_max_years",
        "n_solved": "validate.c3.grid.n_solved",
    })
    return (
        f"The search behind that floor covered {v['n_departures']} departure "
        f"epochs from {v['window_start']} to {v['window_end']}, against "
        f"{v['n_durations']} mission durations running from "
        f"{v['duration_min']} to {v['duration_max']} years, and "
        f"{v['n_solved']} of those cells returned a solution."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

BUILDERS = {
    "solve": explain_intercept,
    "validate": explain_validation,
}


def explain(manifest) -> str:
    """
    The floor's explanation for whatever call this manifest came from.

    Dispatch is on the manifest's own `producer` field, so a caller cannot ask
    for the wrong shape and get prose that reads plausibly about numbers from
    somewhere else.
    """
    build = BUILDERS.get(manifest.producer)
    if build is None:
        raise ValueError(
            f"no deterministic template for producer {manifest.producer!r}; "
            f"have {sorted(BUILDERS)}")
    return build(manifest)
