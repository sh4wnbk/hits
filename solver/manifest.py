"""
solver/manifest.py — the manifest of every citable number for a solver call.

Contract: docs/MANIFEST.md. That document is authoritative; this module
implements it.

The manifest is the single source of grounding. An explanation may quote a
number only if the number appears here. Because the gate that enforces this is
forbidden to do arithmetic, two obligations land on this module:

  1. Every derived number an explanation might say (differences, percentages,
     tolerances, unit conversions) is computed HERE and emitted as its own
     entry. The gate never re-derives one.
  2. Every string an explanation is permitted to write for a number is
     enumerated HERE, by the rendering ladder. The gate never rounds.

Reads the public surface only: SolveResult, GridResult, FrameGateResult,
C3Result, ArrivalResult. Never imports solver.lambert, never touches raw
frames.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

MANIFEST_VERSION = "1.0.0"

FIDELITY_NOTE = (
    "Patched-conic, two-body. No n-body integration and no non-gravitational "
    "forces. A manifest entry records what the solver computed, which is not a "
    "claim that the number is correct to the precision it is quoted at."
)

# Closed unit lexicon (docs/MANIFEST.md).
UNITS = (
    "km/s", "km^2/s^2", "km", "AU", "d", "yr", "JD", "%", "deg",
    "calendar_year", "1",
)

# Units that denote a physical measurement, as opposed to a label, an index,
# or a bare count. Only these get the integral one-decimal rendering.
PHYSICAL_UNITS = ("km/s", "km^2/s^2", "km", "AU", "d", "yr", "deg", "%")

FRAMES = ("earth_relative", "target_relative", "heliocentric", "n_a")

KINDS = ("computed", "derived", "published", "tolerance", "epoch", "count",
         "metadata")


# ---------------------------------------------------------------------------
# The rendering ladder
# ---------------------------------------------------------------------------

def _significant_digits(s: str) -> int:
    """
    Significant digits in a plain decimal rendering.

    Leading zeros are not significant; trailing zeros after a decimal point
    are. "714" -> 3, "0.64" -> 2, "0.6" -> 1, "26" -> 2, "0.04400" -> 4.
    """
    body = s.lstrip("+-").replace(".", "").lstrip("0")
    return len(body)


def _keep_rung(s: str) -> bool:
    """
    Ladder rule 4: keep a rung with three or more significant digits, or with
    exactly two significant digits and a fractional part.

    The two-with-a-fraction clause is what admits "1.6" for 1.62 while
    excluding a bare "26" for 26.28614 and "0.6" for 0.64166. That exclusion is
    the point: 0.6 km/s is Lyra's published Sample B figure, a different entry
    with a different kind, and HITS's computed 0.64166 must not be quotable as
    it.
    """
    sig = _significant_digits(s)
    if sig >= 3:
        return True
    return sig == 2 and "." in s


def build_renderings(raw: float, precision: int) -> List[str]:
    """
    Every string an explanation may write for this number. Ladder policy in
    docs/MANIFEST.md.

    The ladder is the reason the gate can be a pure membership test. Rounding
    happens once, here, in the layer that owns the number.
    """
    v = round(float(raw), precision)

    # Rule 2: start at the decimals the value actually needs, capped at the
    # declared precision. Prevents a value of 0.044 held at precision 5 from
    # emitting "0.04400", which would be precision inflation the gate is
    # elsewhere required to reject.
    at_precision = f"{v:.{precision}f}"
    if "." in at_precision:
        stripped = at_precision.rstrip("0").rstrip(".")
        d_start = len(stripped.split(".")[1]) if "." in stripped else 0
    else:
        d_start = 0

    out: List[str] = []
    for d in range(d_start, -1, -1):
        s = f"{v:.{d}f}"
        # Rule 5: a rung ending in a trailing zero after the decimal point is
        # never natural prose, and dropping it removes any ambiguity with the
        # precision-inflation reject code. The canonical rung cannot end in one
        # by construction.
        if "." in s and s.endswith("0") and d != d_start:
            continue
        if d == d_start or _keep_rung(s):
            out.append(s)

    # Dedupe, preserving ladder order.
    seen, ladder = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            ladder.append(s)
    return ladder


def _with_integral_decimal(ladder: List[str], value: float, unit: str) -> List[str]:
    """
    Ladder rule 6: a physical quantity whose canonical value is integral also
    renders with one decimal.

    A 15-year flight time is written "15 years" and "15.0 years" with equal
    correctness, and rejecting the second would be a false positive on prose
    that is not wrong about anything. Counts, Julian Dates, and calendar years
    are excluded: "391.0 states" and "2027.0" are not prose anyone writes.
    """
    if unit not in PHYSICAL_UNITS:
        return ladder
    if float(value) != int(float(value)):
        return ladder
    one_dp = f"{float(value):.1f}"
    return ladder + [one_dp] if one_dp not in ladder else ladder


# ---------------------------------------------------------------------------
# Entry and Manifest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ManifestEntry:
    id: str
    label: str
    value: float
    precision: int
    unit: str
    frame: str
    kind: str
    renderings: List[str]
    citation: str = ""
    provenance: str = ""

    def __post_init__(self) -> None:
        assert self.unit in UNITS, f"{self.id}: unit {self.unit!r} outside the lexicon"
        assert self.frame in FRAMES, f"{self.id}: frame {self.frame!r} outside the lexicon"
        assert self.kind in KINDS, f"{self.id}: kind {self.kind!r} outside the lexicon"
        assert self.renderings, f"{self.id}: no renderings"
        if self.kind == "published":
            assert self.citation, f"{self.id}: a published figure needs its citation"

    @property
    def canonical(self) -> str:
        return self.renderings[0]


def entry(
    id: str,
    label: str,
    value: float,
    unit: str,
    kind: str,
    precision: int,
    frame: str = "n_a",
    citation: str = "",
    provenance: str = "",
    renderings: Optional[Sequence[str]] = None,
) -> ManifestEntry:
    """
    Build one entry.

    `renderings` is passed explicitly only for kinds that must not be
    re-rounded: `published`, where quoting a source figure to a precision the
    source did not print would misrepresent it, and `tolerance`, where the
    declared parameter has a conventional written form.
    """
    if renderings is None:
        ladder = build_renderings(value, precision)
        ladder = _with_integral_decimal(ladder, round(float(value), precision), unit)
    else:
        ladder = list(renderings)
    return ManifestEntry(
        id=id,
        label=label,
        value=round(float(value), precision),
        precision=precision,
        unit=unit,
        frame=frame,
        kind=kind,
        renderings=ladder,
        citation=citation,
        provenance=provenance,
    )


@dataclass
class Manifest:
    producer: str
    entries: List[ManifestEntry] = field(default_factory=list)
    manifest_version: str = MANIFEST_VERSION
    call_id: str = ""
    emitted_utc: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    fidelity_note: str = FIDELITY_NOTE
    solver_git_sha: str = ""

    def __post_init__(self) -> None:
        if not self.call_id:
            self.call_id = str(uuid.uuid4())
        if not self.emitted_utc:
            self.emitted_utc = datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        if not self.solver_git_sha:
            self.solver_git_sha = _git_sha()

    # -- lookup -------------------------------------------------------------

    def index(self) -> Dict[str, List[ManifestEntry]]:
        """
        Rendering string to the entries that permit it.

        This is the gate's entire data structure. Collisions are permitted and
        resolved downstream by the unit and frame check.
        """
        idx: Dict[str, List[ManifestEntry]] = {}
        for e in self.entries:
            for r in e.renderings:
                idx.setdefault(r, []).append(e)
        return idx

    def collisions(self) -> Dict[str, List[str]]:
        """Renderings claimed by more than one entry, logged so they stay visible."""
        return {r: [e.id for e in es] for r, es in self.index().items() if len(es) > 1}

    def by_id(self, entry_id: str) -> ManifestEntry:
        for e in self.entries:
            if e.id == entry_id:
                return e
        raise KeyError(entry_id)

    def canonical(self, entry_id: str) -> str:
        """The canonical rendering. Printers use this so output cannot drift."""
        return self.by_id(entry_id).canonical

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "call_id": self.call_id,
            "emitted_utc": self.emitted_utc,
            "producer": self.producer,
            "inputs": self.inputs,
            "fidelity_note": self.fidelity_note,
            "solver_git_sha": self.solver_git_sha,
            "entries": [asdict(e) for e in self.entries],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Manifest":
        m = cls(
            producer=d["producer"],
            manifest_version=d["manifest_version"],
            call_id=d["call_id"],
            emitted_utc=d["emitted_utc"],
            inputs=d.get("inputs", {}),
            fidelity_note=d.get("fidelity_note", FIDELITY_NOTE),
            solver_git_sha=d.get("solver_git_sha", ""),
        )
        m.entries = [ManifestEntry(**e) for e in d["entries"]]
        return m

    @classmethod
    def from_json(cls, s: str) -> "Manifest":
        return cls.from_dict(json.loads(s))


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Emitters: public solver results to manifest
# ---------------------------------------------------------------------------
#
# Every derived quantity an explanation might reach for is computed here and
# emitted as an entry, because the gate is forbidden to derive one. If a
# percentage, a difference, a unit conversion, or a tolerance in another form
# is missing from this list, an explanation that states it correctly will be
# rejected, and that is the intended failure direction: a missing entry is a
# visible false positive, whereas a permissive gate is an invisible false
# negative.

DAYS_PER_YEAR = 365.25


def _iso_date(jd_tdb: float) -> str:
    from astropy.time import Time
    return Time(jd_tdb, format="jd", scale="tdb").iso[:10]


def _epoch_entries(prefix: str, label: str, jd_tdb: float,
                   provenance: str) -> List[ManifestEntry]:
    """
    An epoch yields three entries: the Julian Date, the ISO calendar date, and
    the year alone.

    The year is an entry rather than an exemption. docs/MANIFEST.md records why:
    "arrives in 2050" against a real 2037 arrival has to fail, and it can only
    fail if years are grounded like any other quantity.

    The Julian Date carries an explicit single rendering. A JD is an instant,
    and rounding 2461557.5 to 2461558 moves it half a day, so the ladder's
    coarser rungs are not offered for it.
    """
    iso = _iso_date(jd_tdb)
    year = int(iso[:4])
    return [
        entry(f"{prefix}.jd", f"{label} (TDB Julian Date)", jd_tdb, "JD", "epoch",
              precision=1, provenance=provenance,
              renderings=[f"{jd_tdb:.1f}"]),
        entry(f"{prefix}.iso", f"{label} (calendar date, TDB)", float(year), "1",
              "epoch", precision=0, provenance=provenance, renderings=[iso]),
        entry(f"{prefix}.year", f"{label} (year)", float(year), "calendar_year",
              "epoch", precision=0, provenance=provenance, renderings=[str(year)]),
    ]


def _frame_gate_entries(fg) -> List[ManifestEntry]:
    p = "solver.validate.FrameGateResult"
    return [
        entry("validate.frame_gate.computed",
              "Heliocentric v_inf of 1I/'Oumuamua at perihelion, computed",
              fg.computed_km_s, "km/s", "computed", precision=5,
              frame="heliocentric", provenance=f"{p}.computed_km_s"),
        entry("validate.frame_gate.published",
              "Heliocentric v_inf of 1I/'Oumuamua, published",
              fg.published_km_s, "km/s", "published", precision=2,
              frame="heliocentric", citation=fg.citation,
              provenance=f"{p}.published_km_s",
              renderings=[f"{fg.published_km_s:g}"]),
        entry("validate.frame_gate.abs_diff",
              "Frame gate absolute difference, computed minus published",
              fg.abs_diff_km_s, "km/s", "derived", precision=5,
              frame="heliocentric", provenance=f"{p}.abs_diff_km_s"),
        entry("validate.frame_gate.rel_diff_pct",
              "Frame gate relative difference",
              fg.rel_diff_pct, "%", "derived", precision=3,
              provenance=f"{p}.rel_diff_pct"),
        entry("validate.frame_gate.tolerance",
              "Frame gate tolerance",
              fg.tolerance_km_s, "km/s", "tolerance", precision=1,
              frame="heliocentric", provenance=f"{p}.tolerance_km_s",
              renderings=[f"{fg.tolerance_km_s:g}"]),
    ]


def _c3_branch_entries(c3, branch: str, computed: float, published: float,
                       abs_diff: float, rel_diff: float, tol_frac: float,
                       dep_jd: float, tof_days: float, citation: str,
                       label_prefix: str) -> List[ManifestEntry]:
    p = "solver.validate.C3Result"
    b = f"validate.c3.{branch}"
    tol_abs = tol_frac * published
    out = [
        entry(f"{b}.computed", f"{label_prefix} departure C3, computed",
              computed, "km^2/s^2", "computed", precision=2,
              frame="earth_relative", provenance=f"{p}.c3_{branch}_computed_km2_s2"),
        entry(f"{b}.published", f"{label_prefix} departure C3, published",
              published, "km^2/s^2", "published", precision=0,
              frame="earth_relative", citation=citation,
              provenance=f"{p}.c3_{branch}_published_km2_s2",
              renderings=[f"{published:g}"]),
        entry(f"{b}.abs_diff", f"{label_prefix} C3 absolute difference",
              abs_diff, "km^2/s^2", "derived", precision=2,
              frame="earth_relative", provenance=f"{p}.c3_{branch}_abs_diff"),
        entry(f"{b}.rel_diff_pct", f"{label_prefix} C3 relative difference",
              rel_diff, "%", "derived", precision=2,
              provenance=f"{p}.c3_{branch}_rel_diff_pct"),
        entry(f"{b}.tolerance_frac", f"{label_prefix} C3 tolerance, fraction",
              tol_frac, "1", "tolerance", precision=2,
              provenance=f"{p}.c3_{branch}_tolerance_frac",
              renderings=[f"{tol_frac:g}"]),
        entry(f"{b}.tolerance_pct", f"{label_prefix} C3 tolerance, percent",
              tol_frac * 100.0, "%", "tolerance", precision=0,
              provenance=f"derived from {p}.c3_{branch}_tolerance_frac",
              renderings=[f"{tol_frac * 100.0:g}"]),
        entry(f"{b}.tolerance_abs", f"{label_prefix} C3 tolerance, absolute",
              tol_abs, "km^2/s^2", "derived", precision=2,
              frame="earth_relative",
              provenance=f"derived: tolerance_frac * published"),
        entry(f"{b}.tof_days", f"{label_prefix} flight time",
              tof_days, "d", "derived", precision=2,
              provenance=f"{p}.c3_{branch}_tof_days"),
        entry(f"{b}.tof_years", f"{label_prefix} flight time in years",
              tof_days / DAYS_PER_YEAR, "yr", "derived", precision=2,
              provenance=f"derived: {p}.c3_{branch}_tof_days / 365.25"),
    ]
    out += _epoch_entries(f"{b}.departure", f"{label_prefix} departure epoch",
                          dep_jd, f"{p}.c3_{branch}_departure_jd")
    return out


def _c3_entries(c3) -> List[ManifestEntry]:
    out = _c3_branch_entries(
        c3, "y2027", c3.c3_2027_computed_km2_s2, c3.c3_2027_published_km2_s2,
        c3.c3_2027_abs_diff, c3.c3_2027_rel_diff_pct, c3.c3_2027_tolerance_frac,
        c3.c3_2027_departure_jd, c3.c3_2027_tof_days, c3.c3_2027_citation,
        "2027 launch")
    out += _c3_branch_entries(
        c3, "floor", c3.c3_floor_computed_km2_s2, c3.c3_floor_published_km2_s2,
        c3.c3_floor_abs_diff, c3.c3_floor_rel_diff_pct, c3.c3_floor_tolerance_frac,
        c3.c3_floor_departure_jd, c3.c3_floor_tof_days, c3.c3_floor_citation,
        "C3 floor")
    return out


def _arrival_entries(ar, sample: str) -> List[ManifestEntry]:
    from solver.lyra import LYRA_CONSTANTS
    p = "solver.validate.ArrivalResult"
    b = f"validate.arrival_{sample}"
    L = f"Sample {sample.upper()}"
    cfg = LYRA_CONSTANTS[f"v_arr_sample_{sample}_km_s"]
    out = [
        entry(f"{b}.v_inf2", f"{L} arrival relative velocity, eq.4 asymptotic",
              ar.v_inf2_km_s, "km/s", "computed", precision=5,
              frame="target_relative", provenance=f"{p}.v_inf2_km_s"),
        entry(f"{b}.v_arr_local", f"{L} local encounter relative velocity",
              ar.v_arr_local_km_s, "km/s", "computed", precision=5,
              frame="target_relative", provenance=f"{p}.v_arr_local_km_s"),
        entry(f"{b}.published", f"{L} arrival relative velocity, published",
              ar.published_km_s, "km/s", "published", precision=1,
              frame="target_relative", citation=ar.citation,
              provenance=f"{p}.published_km_s",
              renderings=[f"{ar.published_km_s:g}"]),
        entry(f"{b}.abs_diff", f"{L} absolute difference, eq.4 versus published",
              ar.abs_diff_km_s, "km/s", "derived", precision=5,
              frame="target_relative", provenance=f"{p}.abs_diff_km_s"),
        entry(f"{b}.rel_diff_pct", f"{L} relative difference",
              ar.rel_diff_pct, "%", "derived", precision=3,
              provenance=f"{p}.rel_diff_pct"),
        entry(f"{b}.tolerance", f"{L} tolerance",
              ar.tolerance_km_s, "km/s", "tolerance", precision=1,
              frame="target_relative", provenance=f"{p}.tolerance_km_s",
              renderings=[f"{ar.tolerance_km_s:g}"]),
        entry(f"{b}.definitional_gap", f"{L} definitional gap, eq.4 minus local",
              ar.definitional_gap_km_s, "km/s", "derived", precision=5,
              frame="target_relative", provenance=f"{p}.definitional_gap_km_s"),
        entry(f"{b}.encounter_distance_au", f"{L} encounter heliocentric distance",
              ar.encounter_distance_au, "AU", "computed", precision=3,
              frame="heliocentric", provenance=f"{p}.encounter_distance_au"),
        entry(f"{b}.tof_days", f"{L} flight time",
              ar.tof_days, "d", "computed", precision=2,
              provenance=f"{p}.tof_days"),
        entry(f"{b}.tof_years", f"{L} flight time in years",
              ar.tof_days / DAYS_PER_YEAR, "yr", "derived", precision=2,
              provenance=f"derived: {p}.tof_days / 365.25"),
    ]
    # The paper's own stated flight time and encounter distance. Emitted
    # separately from HITS's computed values because they differ, and the
    # difference is a result to be reported rather than smoothed over: 365 days
    # is 0.99932 Julian years against the paper's 1.0, and the 2026 orbit
    # solution puts Sample B's encounter at 115.079 AU against the paper's
    # 111.4 AU, which is orbit-solution drift and not solver error.
    out += [
        entry(f"{b}.published_tof_years", f"{L} flight time, published",
              cfg["published_tof_years"], "yr", "published", precision=1,
              citation=cfg["citation"], provenance="solver.lyra.LYRA_CONSTANTS",
              renderings=[f'{cfg["published_tof_years"]:.1f}',
                          f'{cfg["published_tof_years"]:g}']),
        entry(f"{b}.published_encounter_au",
              f"{L} encounter heliocentric distance, published",
              cfg["published_encounter_au"], "AU", "published", precision=1,
              frame="heliocentric", citation=cfg["citation"],
              provenance="solver.lyra.LYRA_CONSTANTS",
              renderings=[f'{cfg["published_encounter_au"]:g}']),
    ]
    out += _epoch_entries(f"{b}.launch", f"{L} launch epoch",
                          ar.launch_epoch_jd, f"{p}.launch_epoch_jd")
    out += _epoch_entries(f"{b}.arrival", f"{L} arrival epoch",
                          ar.arrival_epoch_jd, f"{p}.arrival_epoch_jd")
    return out


def _grid_entries(g) -> List[ManifestEntry]:
    """
    Grid extents. An explanation that describes the search space is quoting
    numbers, so the search space has to be in the manifest too.
    """
    import numpy as np
    p = "solver.grid.GridResult"
    n_dep, n_tof = g.c3_grid.shape
    dep_first, dep_last = float(g.departure_jds[0]), float(g.departure_jds[-1])
    tof_first = float(g.tof_days[0]) / DAYS_PER_YEAR
    tof_last = float(g.tof_days[-1]) / DAYS_PER_YEAR
    solved = int(np.count_nonzero(~np.isnan(g.c3_grid)))
    out = [
        entry("validate.c3.grid.n_departures", "C3 grid departure epochs",
              float(n_dep), "1", "count", precision=0,
              provenance=f"{p}.c3_grid.shape[0]"),
        entry("validate.c3.grid.n_durations", "C3 grid duration values",
              float(n_tof), "1", "count", precision=0,
              provenance=f"{p}.c3_grid.shape[1]"),
        entry("validate.c3.grid.n_cells", "C3 grid cells",
              float(n_dep * n_tof), "1", "count", precision=0,
              provenance="derived: n_departures * n_durations"),
        entry("validate.c3.grid.n_solved", "C3 grid cells with a solution",
              float(solved), "1", "count", precision=0,
              provenance="derived: non-NaN cells of c3_grid"),
        entry("validate.c3.grid.duration_min_years", "C3 grid shortest duration",
              tof_first, "yr", "metadata", precision=2,
              provenance=f"{p}.tof_days[0] / 365.25"),
        entry("validate.c3.grid.duration_max_years", "C3 grid longest duration",
              tof_last, "yr", "metadata", precision=2,
              provenance=f"{p}.tof_days[-1] / 365.25"),
    ]
    out += _epoch_entries("validate.c3.grid.launch_window_start",
                          "C3 grid earliest launch", dep_first,
                          f"{p}.departure_jds[0]")
    out += _epoch_entries("validate.c3.grid.launch_window_end",
                          "C3 grid latest launch", dep_last,
                          f"{p}.departure_jds[-1]")
    return out


def _source_entries(retrieval_date: str) -> List[ManifestEntry]:
    """
    Bibliographic and retrieval years, so "the 2019 paper" and "the 2026
    retrieval" ground against data rather than needing a prose exemption.
    """
    from solver.lyra import PUBLICATION_YEAR
    out = [
        entry("source.lyra.publication_year", "Lyra source publication year",
              float(PUBLICATION_YEAR), "calendar_year", "metadata", precision=0,
              provenance="solver.lyra.PUBLICATION_YEAR",
              renderings=[str(PUBLICATION_YEAR)]),
    ]
    if retrieval_date and len(retrieval_date) >= 4 and retrieval_date[:4].isdigit():
        y = int(retrieval_date[:4])
        out.append(entry("source.horizons.retrieval_year",
                         "Horizons retrieval year", float(y), "calendar_year",
                         "metadata", precision=0,
                         provenance="StateVector.retrieved_utc",
                         renderings=[str(y)]))
        out.append(entry("source.horizons.retrieval_date",
                         "Horizons retrieval date", float(y), "1", "metadata",
                         precision=0, provenance="StateVector.retrieved_utc",
                         renderings=[retrieval_date[:10]]))
    return out


def from_validation_results(results, inputs: Optional[Dict[str, Any]] = None) -> Manifest:
    """
    Build the manifest for a full validate() call.

    Reads solver.validate.ValidationResults and nothing deeper.
    """
    entries: List[ManifestEntry] = []
    entries += _frame_gate_entries(results.frame_gate)
    if results.c3 is not None:
        entries += _c3_entries(results.c3)
    if results.grid_result is not None:
        entries += _grid_entries(results.grid_result)
    if results.arrival_a is not None:
        entries += _arrival_entries(results.arrival_a, "a")
    if results.arrival_b is not None:
        entries += _arrival_entries(results.arrival_b, "b")
    entries += _source_entries(results.retrieval_date)

    return Manifest(producer="validate", entries=entries, inputs=inputs or {})


def from_solve_result(result, inputs: Optional[Dict[str, Any]] = None) -> Manifest:
    """Build the manifest for a single solve() call."""
    p = "solver.solve.SolveResult"
    entries = [
        entry("solve.c3", "Departure C3", result.c3_km2_s2, "km^2/s^2",
              "computed", precision=2, frame="earth_relative",
              provenance=f"{p}.c3_km2_s2"),
        entry("solve.dv_depart", "Departure hyperbolic excess speed",
              result.dv_depart_km_s, "km/s", "computed", precision=5,
              frame="earth_relative", provenance=f"{p}.dv_depart_km_s"),
        entry("solve.v_arr", "Local encounter relative velocity",
              result.v_arr_km_s, "km/s", "computed", precision=5,
              frame="target_relative", provenance=f"{p}.v_arr_km_s"),
        entry("solve.v_inf2", "Arrival relative velocity, eq.4 asymptotic",
              result.v_inf2_km_s, "km/s", "computed", precision=5,
              frame="target_relative", provenance=f"{p}.v_inf2_km_s"),
        entry("solve.tof_days", "Flight time", result.tof_days, "d", "computed",
              precision=2, provenance=f"{p}.tof_days"),
        entry("solve.tof_years", "Flight time in years",
              result.tof_days / DAYS_PER_YEAR, "yr", "derived", precision=2,
              provenance=f"derived: {p}.tof_days / 365.25"),
    ]
    entries += _epoch_entries("solve.departure", "Departure epoch",
                              result.departure_epoch_jd, f"{p}.departure_epoch_jd")
    entries += _epoch_entries("solve.arrival", "Arrival epoch",
                              result.arrival_epoch_jd, f"{p}.arrival_epoch_jd")
    return Manifest(producer="solve", entries=entries, inputs=inputs or {})


# ---------------------------------------------------------------------------
# Fixture freezing
# ---------------------------------------------------------------------------

def freeze_validate_fixture(path: str = "tests/fixtures/manifests/validate_full.json") -> str:
    """
    Emit the committed validate() manifest the adversarial corpus is judged
    against.

    `call_id`, `emitted_utc`, and `solver_git_sha` are pinned to fixed values,
    because a fixture that changes on every run cannot be diffed and would make
    a real drift in the numbers invisible inside the noise.
    """
    import os
    from solver.fetch import load_state_vectors
    from solver.validate import validate, _manifest_inputs

    svs = load_state_vectors("data/state_vectors.json")
    results = validate(svs, verbose=False)
    m = results.manifest
    m.call_id = "frozen-validate-full"
    m.emitted_utc = "frozen"
    m.solver_git_sha = "frozen"

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(m.to_json() + "\n")
    return path


if __name__ == "__main__":
    import sys
    if "--freeze" in sys.argv:
        out = freeze_validate_fixture()
        print(f"frozen: {out}")
    else:
        print(__doc__)
