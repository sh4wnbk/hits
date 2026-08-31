"""
solver/frozen.py — read the committed per-object intercept envelopes.

The serving counterpart to data/freeze_manifests.py. That script runs the
solver, which means numpy, astropy, hapsira and scipy; this module reads what
it wrote, which means json. A deployed web process imports this and never the
other, so the accessibility gate in CLAUDE.md ("no clone, no virtual
environment, works on a phone") extends to the machine serving the answer:
nothing about answering a question requires the stack that computed it.

The rule is enforced, not intended. This module may import solver.manifest and
solver.objects, both stdlib-only, and nothing else from solver. A test asserts
that loading a frozen envelope and running the floor and the gate over it pulls
in no top-level numpy, astropy, hapsira or scipy.

## What a frozen envelope is

InterceptResult.to_dict(), verbatim. The manifest and, beside it rather than
inside it, the verification status. solver/objects.py is explicit that a claim
about the literature is not a manifest entry, and freezing preserves that
separation: a renderer reads `verification_status` off the envelope, the gate
reads renderings out of the manifest, and the agent can quote the second and
never the first.

## The call_id is pinned by the freeze

`check()` is scoped to one manifest's call_id, and the three objects overlap
enough in magnitude that the scoping is load-bearing rather than theoretical.
Reading a frozen envelope reconstructs the call_id that was written, so an
answer produced against the committed file is checkable against the committed
file. It is not a fresh call and does not pretend to be.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from solver import objects
from solver.manifest import Manifest

# Committed location. Relative to the repository root, which is the working
# directory the service starts in.
MANIFEST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "manifests")


@dataclass(frozen=True)
class FrozenIntercept:
    """
    One committed intercept envelope, loaded.

    Carries the same fields InterceptResult serializes, minus the SolveResult,
    which is not serialized and is not needed: every number a surface prints
    comes from the manifest by entry id, never from the result object. Dropping
    it is what lets the read side stay stdlib-only.
    """
    key: str
    designation: str
    horizons_id: str
    discovery_year: int
    verification_status: str
    verification_basis: str
    transfer_basis: str
    manifest: Manifest

    @property
    def call_id(self) -> str:
        return self.manifest.call_id

    @property
    def is_validated(self) -> bool:
        """True only where a published figure exists to have been checked against."""
        return self.verification_status == objects.VALIDATED

    def to_dict(self) -> Dict[str, Any]:
        """Round-trips back to the committed file's shape."""
        return {
            "object": {
                "key": self.key,
                "designation": self.designation,
                "horizons_id": self.horizons_id,
                "discovery_year": self.discovery_year,
            },
            "verification_status": self.verification_status,
            "verification_basis": self.verification_basis,
            "transfer_basis": self.transfer_basis,
            "manifest": self.manifest.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FrozenIntercept":
        obj = d["object"]
        return cls(
            key=obj["key"],
            designation=obj["designation"],
            horizons_id=obj["horizons_id"],
            discovery_year=obj["discovery_year"],
            verification_status=d["verification_status"],
            verification_basis=d["verification_basis"],
            transfer_basis=d["transfer_basis"],
            manifest=Manifest.from_dict(d["manifest"]),
        )


def path_for(key: str, manifest_dir: str = MANIFEST_DIR) -> str:
    """The committed file for a key, after checking the key is one of the three."""
    objects.get(key)          # raises with the whole permitted set named
    return os.path.join(manifest_dir, f"{key}.json")


def load(key: str, manifest_dir: str = MANIFEST_DIR) -> FrozenIntercept:
    """
    The committed envelope for one object.

    KeyError for a key outside the committed set, with the three keys named.
    FileNotFoundError if the freeze has not been run, pointing at the script
    that runs it, because a missing frozen file is a build step that was
    skipped and not a bad request.
    """
    path = path_for(key, manifest_dir)
    try:
        with open(path) as fh:
            d = json.load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{path} is missing. Run: python data/freeze_manifests.py"
        ) from None
    fi = FrozenIntercept.from_dict(d)
    if fi.key != key:
        raise ValueError(
            f"{path} holds object {fi.key!r} but was loaded as {key!r}. The "
            "frozen envelopes and their filenames have diverged.")
    return fi


def load_all(manifest_dir: str = MANIFEST_DIR) -> Tuple[FrozenIntercept, ...]:
    """The three, in discovery order."""
    return tuple(load(k, manifest_dir) for k in objects.KEYS)
