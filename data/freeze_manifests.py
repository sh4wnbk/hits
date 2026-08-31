"""
data/freeze_manifests.py — freeze the three per-object intercept manifests to
committed JSON.

Build-time only. This script imports the whole scientific stack, because
building a manifest means running the solver; the serving path that reads what
it writes imports none of it. That asymmetry is the point. A web process that
answers "what does the transfer to 3I/ATLAS cost" should not need hapsira
installed to do it, and after this script has run it does not.

## What gets frozen

The whole InterceptResult envelope, not the manifest alone. `verification_status`
is deliberately not a manifest entry (solver/objects.py says why: a claim about
the literature is not a number the solver computed), so freezing only the
manifest would drop the one field that keeps 'Oumuamua's published-figure
validation from being silently lent to the two objects that have none.

## The call_id

Frozen per object, once, and not regenerated on read. `check()` is scoped to a
call_id, and pinning it is what lets the committed corpus of an object's own
answer stay valid against the committed manifest. A freeze that reran uuid4 on
every load would make the frozen file a different call from the one the tests
were written against.

Run:  python data/freeze_manifests.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver import objects
from solver.fetch import load_state_vectors
from solver.intercept import intercept

OUT_DIR = "data/manifests"


def freeze(out_dir: str = OUT_DIR) -> list:
    svs = load_state_vectors("data/state_vectors.json")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for key in objects.KEYS:
        ir = intercept(key, svs)
        path = os.path.join(out_dir, f"{key}.json")
        with open(path, "w") as fh:
            fh.write(json.dumps(ir.to_dict(), indent=2) + "\n")
        written.append((path, ir.call_id, len(ir.manifest.entries)))
    return written


if __name__ == "__main__":
    for path, call_id, n in freeze():
        print(f"{path}: {n} entries, call_id {call_id}")
