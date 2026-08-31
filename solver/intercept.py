"""
solver/intercept.py — one intercept answer for one committed object.

This is the shape a surface renders: the object, the transfer, the manifest of
every citable number, and the verification status that says what backs it. It
is the layer above solve() and below the agent, and it exists so that the
per-object provenance travels with the numbers instead of being reattached by
whoever draws the page.

## Why the call_id matters here

`check(text, manifest)` is scoped to one manifest, and docs/MANIFEST.md is
explicit that this is what stops an explanation borrowing a plausible figure
from a neighbouring run. With three objects live at once that stops being a
theoretical concern: 2I/Borisov and 3I/ATLAS are solved at the same flight
time, so their manifests carry the same 7305 and the same 20, and their C3
figures are the same order of magnitude. Each intercept builds its own
manifest with its own call_id, so a Borisov figure appearing in an ATLAS
explanation is ungrounded, and tests/test_intercept.py proves it rather than
assuming it.

## Why verification_status is on the result and not in the manifest

The manifest holds numbers the solver computed. "No published intercept study
exists to validate against" is a claim about the literature, not an output of
the solver, and an entry for it would be a claim the agent could quote with
the solver's authority behind it. It rides on the envelope instead, where a
judges page and a UI can render it per object and the agent cannot cite it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from solver import manifest as manifest_mod
from solver.fetch import StateVector
from solver.objects import InterstellarObject, get as get_object
from solver.solve import SolveResult, solve


@dataclass(frozen=True)
class InterceptResult:
    """
    One object's intercept answer, with its provenance attached.

    `verification_status` is duplicated out of `obj` deliberately. It is the
    field a renderer reads, and a renderer that has to reach through a nested
    object to find out whether a number was ever checked is a renderer that
    will eventually forget to.
    """
    obj: InterstellarObject
    result: SolveResult
    manifest: manifest_mod.Manifest
    verification_status: str
    verification_basis: str

    @property
    def call_id(self) -> str:
        return self.manifest.call_id

    def to_dict(self) -> Dict[str, Any]:
        """
        The serialized form a surface renders. Numbers come from the manifest
        and nowhere else, so a page cannot print a figure at a precision the
        solver did not declare.
        """
        return {
            "object": {
                "key": self.obj.key,
                "designation": self.obj.designation,
                "horizons_id": self.obj.horizons_id,
                "discovery_year": self.obj.discovery_year,
            },
            "verification_status": self.verification_status,
            "verification_basis": self.verification_basis,
            "transfer_basis": self.obj.transfer_basis,
            "manifest": self.manifest.to_dict(),
        }


def intercept(key: str, state_vectors: Dict[str, Any]) -> InterceptResult:
    """
    Solve the committed transfer for one object and build its manifest.

    Parameters
    ----------
    key : str
        One of solver.objects.KEYS. Anything else raises, because the set of
        objects is committed and there is no free-text target.
    state_vectors : dict
        Loaded data/state_vectors.json, as solver.fetch.load_state_vectors
        returns it.
    """
    obj = get_object(key)

    earth_sv = _single(state_vectors, obj.earth_key)
    target_sv = _single(state_vectors, obj.target_key)

    expected_tof = target_sv.epoch_tdb_jd - earth_sv.epoch_tdb_jd
    if abs(expected_tof - obj.tof_days) > 1e-6:
        raise ValueError(
            f"{obj.designation}: committed states are {expected_tof} days apart "
            f"but the object declares a flight time of {obj.tof_days} days. The "
            "transfer and the states it reads have diverged.")

    result = solve(earth_sv, target_sv, obj.tof_days)

    m = manifest_mod.from_solve_result(result, inputs={
        "object_key": obj.key,
        "designation": obj.designation,
        "earth_state_key": obj.earth_key,
        "target_state_key": obj.target_key,
        "earth_state_epoch": earth_sv.epoch_iso,
        "target_state_epoch": target_sv.epoch_iso,
        "retrieved_utc": target_sv.retrieved_utc,
    })

    return InterceptResult(
        obj=obj,
        result=result,
        manifest=m,
        verification_status=obj.verification_status,
        verification_basis=obj.verification_basis,
    )


def _single(state_vectors: Dict[str, Any], key: str) -> StateVector:
    try:
        sv = state_vectors[key]
    except KeyError:
        raise KeyError(
            f"committed state vector {key!r} is missing. Run "
            "data/fetch_objects.py.") from None
    if isinstance(sv, list):
        raise TypeError(
            f"{key!r} is a window of {len(sv)} states; an intercept reads one "
            "pinned epoch.")
    return sv
