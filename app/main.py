"""
app/main.py — the HITS web service.

One URL, three objects, no setup. CLAUDE.md makes accessibility a design gate
rather than a final phase, and this module is where that gate is either kept or
lost: a reader with a phone and no account gets the same numbers a judge with a
clone gets, because the numbers were computed before deployment and committed.

## What this process is allowed to import

Not the solver. `data/freeze_manifests.py` ran numpy, astropy, hapsira and
scipy once, at build time, and committed the result; this process reads json.
tests/test_serve_imports.py asserts it, and the assertion is load-bearing
rather than tidy: a free web instance has neither the memory nor the build
minutes for the scientific stack, and an import added here would take the
deployment down at a moment when nobody was looking at this file.

## Credentials

None are read here, and none are set in render.yaml. `explain(manifest,
client=None)` consults the environment through agent/granite.py, finds nothing,
and serves the deterministic floor. That is not a degraded mode being tolerated:
it is the path that reproduces byte-for-byte with no credentials and no
network, and it is the one the README shows.

`served_by` travels to every response that carries an explanation, so a reader
can never mistake which path produced the prose. CLAUDE.md requires offline and
credentialed results to be reported separately, and a field is how that
requirement survives contact with a browser.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from agent.explain import explain
from app.gate_demo import gate_demo
from solver import objects
from solver.frozen import FrozenIntercept, load

TITLE = "HITS | Hyperbolic Intercept & Trajectory Solver"
TAGLINE = "Can we catch it?"
REPO_URL = "https://github.com/sh4wnbk/hits"

app = FastAPI(
    title=TITLE,
    description=(
        "Trajectory analysis for the three known interstellar objects. Every "
        "number is computed by a deterministic solver and checked against a "
        "manifest before it is served."
    ),
)


def _frozen(object_key: str) -> FrozenIntercept:
    """
    The committed envelope for a requested key, or 404 naming the whole set.

    The set is closed and there is no free-text target (solver/objects.py gives
    the reason: an answer is only as good as the state vectors behind it, and
    these are committed and frame-checked). A caller who mistyped is better
    served by the three keys than by a bare not-found.

    The routes matching this take a `:path` parameter so a slash reaches here
    rather than missing the route. All three designations contain one, so
    `/explain/2I/Borisov` is the likeliest wrong input there is, and it would
    otherwise collect the framework's bare "Not Found" instead of the sentence
    naming the keys. Nothing is resolved from the extra segments: the key is
    looked up in a committed dict, so a traversal-shaped path is a KeyError
    like any other miss.
    """
    try:
        return load(object_key)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{object_key!r} is not one of the interstellar objects HITS "
                f"computes for. The set is fixed at {list(objects.KEYS)} and "
                "takes no free-text target."
            ),
        ) from None


@app.get("/health")
def health() -> Dict[str, str]:
    """Liveness. Cheap on purpose: a keepalive ping should not load a manifest."""
    return {"status": "ok"}


@app.get("/objects")
def list_objects() -> Dict[str, Any]:
    """
    The three, in discovery order, each with what backs its numbers.

    `verification_status` is on every entry rather than a footnote on the page,
    because the three objects are not equally well backed and a list that
    presented them identically would lend 'Oumuamua's published-figure
    validation to two objects that have none.
    """
    out = []
    for key in objects.KEYS:
        fi = load(key)
        out.append({
            "key": fi.key,
            "designation": fi.designation,
            "discovery_year": fi.discovery_year,
            "verification_status": fi.verification_status,
            "verification_basis": fi.verification_basis,
            "transfer_basis": fi.transfer_basis,
        })
    return {"objects": out}


@app.get("/explain/{object_key:path}")
def explain_object(object_key: str) -> Dict[str, Any]:
    """
    One object's intercept answer, gated before it is returned.

    `served_by` is `deterministic_floor` on this deployment, because no watsonx
    credential is set. It is reported rather than assumed: a response that only
    carried prose could not tell a reader which path wrote it.
    """
    fi = _frozen(object_key)
    e = explain(fi.manifest, client=None)
    return {
        "object": fi.key,
        "designation": fi.designation,
        "text": e.text,
        "served_by": e.served_by,
        "floor_reason": e.floor_reason,
        "grounded": e.grounded,
        "verification_status": fi.verification_status,
        "verification_basis": fi.verification_basis,
        "call_id": fi.call_id,
    }


@app.get("/gate/demo/{object_key:path}")
def gate_demo_endpoint(object_key: str) -> Dict[str, Any]:
    """
    Watch the number check accept a real figure and reject an invented one.

    The judges-facing exhibit for CLAUDE.md's first non-negotiable. Two
    candidates, differing by one digit of one figure, run through the same
    `verify.groundedness.check` that gates every explanation this service
    serves. No watsonx, no credential, no model: the verdict is a comparison
    against the manifest, and a reader can see the comparison being made rather
    than being told it happens.
    """
    return gate_demo(_frozen(object_key))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """
    A placeholder, and deliberately a bare one.

    No figure appears on this page. Everything HITS states about an object is
    the output of a gated explanation, and a number typed into a template here
    would be the first ungrounded number in the system. The chips, the Open
    Graph card and the noscript path land in the next handoff, with the numbers
    coming from /explain.
    """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<style>
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 34rem;
         margin: 4rem auto; padding: 0 1.25rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 .25rem; }}
  p.tagline {{ font-size: 1.6rem; margin: 0 0 1.5rem; font-weight: 600; }}
  a {{ color: #1a4fd8; }}
  ul {{ padding-left: 1.2rem; }}
  code {{ background: #f2f2f2; padding: .1rem .3rem; border-radius: 3px; }}
</style>
</head>
<body>
<h1>{TITLE}</h1>
<p class="tagline">{TAGLINE}</p>
<p>HITS computes what it would cost to send a probe to an interstellar
object, and explains the answer in plain language. The trajectory is solved
deterministically; every number in the explanation is checked against the
solver's output before it is shown.</p>
<ul>
  <li><code>/objects</code> the three objects HITS answers for</li>
  <li><code>/explain/{{object_key}}</code> one object's intercept answer</li>
  <li><code>/gate/demo/{{object_key}}</code> the number check, run live</li>
</ul>
<p><a href="{REPO_URL}">Source and validation on GitHub</a></p>
</body>
</html>
"""
