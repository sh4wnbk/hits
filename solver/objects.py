"""
solver/objects.py — the fixed set of interstellar objects HITS will answer for,
and what backs each answer.

Three objects, because three is how many humanity has found. The set is a
committed constant and not an input. There is no free-text target field
anywhere in HITS, and the reason is the one CLAUDE.md gives for every other
refusal in this repository: an answer is only as good as the state vectors
behind it, and the state vectors here are committed, frame-checked, and
retrieved on a recorded date. A free-text designation would either need a live
Horizons call at request time, which breaks the offline guarantee and makes a
judge's re-run depend on the network, or it would silently resolve to nothing.
`get()` raises on anything outside the set rather than guessing.

## The verification status field

The three objects are not equally well backed, and the difference is the whole
honesty problem of this phase.

'Oumuamua's numbers can be set against Hein et al. 2019, and Phase 1 did that
for five quantities. Borisov and 3I/ATLAS have no published intercept study to
be set against, because nobody has published one. Same solver, same committed
ephemerides, same frame check, no external check on the answer.

That distinction has to survive contact with a user interface, and prose in a
document does not survive it: a judges page renders fields, not paragraphs. So
`verification_status` is a field on the object and on every result computed for
it, carried in the serialized form, and the string for the two unvalidated
objects says plainly that no published study exists rather than going quiet.

It is deliberately not a manifest entry. The manifest is the universe of
citable numbers, and a provenance claim is not a number; putting it there
would make it something the agent could quote as though the solver had
computed it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from solver.lyra import PUBLICATION_REFERENCE

# The two verification statuses. Written once here so the string a judges page
# renders and the string a test asserts on cannot drift apart.
VALIDATED = "computed and validated against published figures (Hein et al. 2019)"
UNVALIDATED = ("computed with the same method; no published intercept study "
               "exists to validate against")


@dataclass(frozen=True)
class InterstellarObject:
    """
    One interstellar object, its committed transfer, and what backs it.

    `earth_key` and `target_key` name entries in data/state_vectors.json. The
    object owns them rather than the caller passing epochs, so the transfer an
    object reports is the transfer that was frame-checked when it was fetched.
    """
    key: str
    designation: str
    horizons_id: str
    discovery_year: int
    earth_key: str
    target_key: str
    tof_days: float
    verification_status: str
    verification_basis: str
    transfer_basis: str

    @property
    def is_validated(self) -> bool:
        """True only where a published figure exists to have been checked against."""
        return self.verification_status == VALIDATED


# The rule behind the two unvalidated transfers, stated once. data/fetch_objects.py
# is where it was executed; this is the sentence a reader is owed alongside the
# numbers it produced.
_CHOSEN_TRANSFER = (
    "no published study to reproduce, so the departure is the cheapest day in "
    "calendar year 2030 at a flight time of 7305 days, twenty years on the "
    "365.25-day year and the duration class of Project Lyra's Sample B. Both "
    "C3 minima are interior to the year, not on its edge."
)

OBJECTS: Dict[str, InterstellarObject] = {
    "oumuamua": InterstellarObject(
        key="oumuamua",
        designation="1I/'Oumuamua",
        horizons_id="1I",
        discovery_year=2017,
        earth_key="earth_sample_ab_launch",
        target_key="oumuamua_sample_a_arrival",
        tof_days=365.0,
        verification_status=VALIDATED,
        verification_basis=PUBLICATION_REFERENCE,
        transfer_basis=(
            "Project Lyra's Sample A: a 2017 departure on a flight of about "
            "one year, the case Hein et al. 2019 publish an arrival relative "
            "velocity for."
        ),
    ),
    "borisov": InterstellarObject(
        key="borisov",
        designation="2I/Borisov",
        horizons_id="2I",
        discovery_year=2019,
        earth_key="earth_borisov_departure",
        target_key="borisov_arrival",
        tof_days=7305.0,
        verification_status=UNVALIDATED,
        verification_basis="",
        transfer_basis=_CHOSEN_TRANSFER,
    ),
    "atlas": InterstellarObject(
        key="atlas",
        designation="3I/ATLAS",
        horizons_id="3I",
        discovery_year=2025,
        earth_key="earth_atlas_departure",
        target_key="atlas_arrival",
        tof_days=7305.0,
        verification_status=UNVALIDATED,
        verification_basis="",
        transfer_basis=_CHOSEN_TRANSFER,
    ),
}

# Discovery order, which is also designation order.
KEYS: Tuple[str, ...] = ("oumuamua", "borisov", "atlas")


def get(key: str) -> InterstellarObject:
    """
    The object for a key, or KeyError naming the whole permitted set.

    The error carries the alternatives because this is the surface a request
    parameter reaches, and a caller who mistyped is better served by the three
    keys than by a bare KeyError.
    """
    try:
        return OBJECTS[key]
    except KeyError:
        raise KeyError(
            f"{key!r} is not one of the interstellar objects HITS computes for. "
            f"The set is fixed at {list(KEYS)} and takes no free-text target."
        ) from None


def all_objects() -> Tuple[InterstellarObject, ...]:
    """The three, in discovery order."""
    return tuple(OBJECTS[k] for k in KEYS)
