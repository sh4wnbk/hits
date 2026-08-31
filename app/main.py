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

## Where an object answer comes from

The committed cache, written by one watched generation per object
(`data/answers/`). Not a live call, because a live call would spend quota on
every page load, take seconds on an instance that may itself be cold-starting,
and return something different next time. `?live=1` opts into a real call for
anyone who wants to watch one happen.

Whichever path answers, `served_by` travels with the prose. CLAUDE.md requires
offline and credentialed results to be reported separately, and a field is how
that requirement survives contact with a browser. The page prints it.

## What the page may claim

Nothing that is not backed by an endpoint or a committed file. The chips come
from app/chips.py with their mined provenance attached, the evidence answers
from data/evidence.json, the object answers from data/answers/. There is no
figure written into the template: every number a reader sees came through the
gate.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse

from agent import granite
from agent.explain import explain
from app import answers as answer_store
from app import chips
from app.gate_demo import gate_demo
from solver import objects
from solver.frozen import FrozenIntercept, load

TITLE = "HITS | Hyperbolic Intercept & Trajectory Solver"
TAGLINE = "Can we catch it?"
REPO_URL = "https://github.com/sh4wnbk/hits"
PUBLIC_URL = "https://hits-f3s4.onrender.com"

SUMMARY = (
    "HITS computes what it would cost to send a probe to an interstellar "
    "object, and explains the answer in plain language. The trajectory is "
    "solved deterministically; every number in the explanation is checked "
    "against the solver's output before it is shown."
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_PATH = os.path.join(REPO_ROOT, "data", "evidence.json")
OG_BANNER_PATH = os.path.join(REPO_ROOT, "docs", "img", "og_banner.png")
INDEX_PATH = os.path.join(REPO_ROOT, "web", "index.html")
GATE_PAGE_PATH = os.path.join(REPO_ROOT, "web", "gate.html")

app = FastAPI(title=TITLE, description=SUMMARY)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

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


def _evidence() -> Dict[str, Any]:
    """The committed evidence answers. Absent before they are written."""
    if not os.path.exists(EVIDENCE_PATH):
        return {}
    with open(EVIDENCE_PATH) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# JSON endpoints
# ---------------------------------------------------------------------------

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
        cached = answer_store.load(key)
        out.append({
            "key": fi.key,
            "designation": fi.designation,
            "discovery_year": fi.discovery_year,
            "verification_status": fi.verification_status,
            "verification_basis": fi.verification_basis,
            "transfer_basis": fi.transfer_basis,
            "answer_cached": cached is not None,
            "served_by": cached.served_by if cached else None,
        })
    return {"objects": out}


@app.get("/explain/{object_key:path}")
def explain_object(
    object_key: str,
    live: int = Query(0, description="1 forces a real Granite call, bypassing the cache"),
) -> Dict[str, Any]:
    """
    One object's intercept answer.

    Default: the committed answer from one watched generation, served instantly
    and without spending quota. `?live=1`: a real call, made now, reported
    honestly including when it falls to the floor.

    `source` distinguishes the two so a reader is never guessing which they got,
    and `served_by` distinguishes Granite from the floor within either.
    """
    fi = _frozen(object_key)

    if not live:
        cached = answer_store.load(fi.key)
        if cached is not None:
            return {
                "object": fi.key,
                "designation": fi.designation,
                "text": cached.text,
                "served_by": cached.served_by,
                "source": "cached",
                "model_id": cached.model_id,
                "generated_at": cached.generated_at,
                "regenerations": cached.regenerations,
                "grounded": cached.verified_grounded,
                "advisory": cached.advisory,
                "floor_reason": "",
                "verification_status": fi.verification_status,
                "verification_basis": fi.verification_basis,
                "call_id": fi.call_id,
            }

    # Either ?live=1, or no cache has been frozen yet. from_env() returns None
    # with no credentials, and explain() then serves the gated floor, so this
    # path works on a deployment that has never seen a watsonx key.
    client = granite.from_env()
    e = explain(fi.manifest, client=client)
    return {
        "object": fi.key,
        "designation": fi.designation,
        "text": e.text,
        "served_by": e.served_by,
        "source": "live" if live else "live-no-cache",
        "model_id": e.model_id,
        "generated_at": "",
        "regenerations": e.regenerations,
        "grounded": e.grounded,
        "advisory": e.verdict.advisory,
        "floor_reason": e.floor_reason,
        "verification_status": fi.verification_status,
        "verification_basis": fi.verification_basis,
        "call_id": fi.call_id,
    }


@app.get("/evidence/{eid:path}")
def evidence(eid: str) -> Dict[str, Any]:
    """
    One evidence answer, served from committed prose.

    These are not gated the way object answers are, and the difference is real
    rather than an oversight: an evidence answer is a claim about the project
    (what a paper says, what has been validated, what an endpoint does), and
    the gate checks numeric tokens against a solver manifest. There is no
    manifest for "Project Lyra exists". So they are written from committed
    artefacts, each answer naming its source, and the sources are checkable.
    """
    store = _evidence()
    key = eid.strip().upper()
    if key not in chips.EVIDENCE_IDS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{eid!r} is not one of the evidence questions. The set is "
                f"fixed at {list(chips.EVIDENCE_IDS)}."
            ),
        )
    if key not in store:
        # A real id whose answer has not been written yet. Distinguished from
        # a bad id on purpose: the two are different problems and a message
        # that named the valid set while refusing a member of it would send a
        # reader looking for a typo that is not there.
        raise HTTPException(
            status_code=404,
            detail=(
                f"{key} is a known evidence question but no answer has been "
                "committed for it yet."
            ),
        )
    chip = chips.evidence_chip(key)
    item = store[key]
    return {
        "eid": key,
        "question": chip.label,
        "mined_from": chip.mined,
        "mined_source": chip.mined_source,
        "text": item["text"],
        "sources": item["sources"],
    }


@app.get("/gate/demo/{object_key:path}")
def gate_demo_endpoint(
    object_key: str,
    request: Request,
    format: str = Query("", description="json or html, overriding what the caller accepts"),
) -> Any:
    """
    Watch the number check accept a real figure and reject an invented one.

    The judges-facing exhibit for CLAUDE.md's first non-negotiable. Two
    candidates, differing by one digit of one figure, run through the same
    `verify.groundedness.check` that gates every explanation this service
    serves. No watsonx, no credential, no model: the verdict is a comparison
    against the manifest, and a reader can see the comparison being made rather
    than being told it happens.

    ## Why this one endpoint answers in two shapes

    The page links a reader here, and a reader who follows a link about honesty
    and lands on a wall of json has been shown the machinery and told nothing.
    So a browser gets the readable view and an API caller gets the data, from
    the same URL and the same computation: `?format=` settles it outright, and
    otherwise the caller's Accept header does. curl asks for anything and gets
    json, which keeps every existing caller working.

    The readable view is a committed file that fetches `?format=json` itself,
    so the two cannot disagree: there is no second rendering of these figures
    anywhere, and no number is written into the file that serves them.

    The key is resolved before the format is, so an unknown object is a 404 in
    either shape rather than a page that loads and then fails.
    """
    fi = _frozen(object_key)

    fmt = format.strip().lower()
    if fmt not in ("", "json", "html"):
        raise HTTPException(
            status_code=400,
            detail=f"format must be 'json' or 'html', not {format!r}",
        )

    if fmt == "json":
        return gate_demo(fi)
    wants_html = fmt == "html" or "text/html" in request.headers.get("accept", "")
    if wants_html:
        if not os.path.exists(GATE_PAGE_PATH):
            raise HTTPException(status_code=404, detail="view not committed")
        return FileResponse(GATE_PAGE_PATH, media_type="text/html; charset=utf-8")
    return gate_demo(fi)


@app.get("/chips")
def list_chips() -> Dict[str, Any]:
    """The page's questions as data, so the page and the API cannot drift."""
    return {
        "corpus_note": chips.CORPUS_NOTE,
        "object_facets": [
            {"key": f.key, "label": f.label, "entry_ids": list(f.entry_ids),
             "mined": f.mined, "mined_source": f.mined_source, "note": f.note}
            for f in chips.OBJECT_FACETS
        ],
        "evidence_chips": [
            {"eid": c.eid, "label": c.label, "mined": c.mined,
             "mined_source": c.mined_source}
            for c in chips.EVIDENCE_CHIPS
        ],
    }


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

@app.get("/static/og_banner.png")
def og_banner() -> FileResponse:
    """
    The card image for og:image.

    Served by an explicit route rather than a mounted static directory. One
    file is needed and mounting docs/img/ would put six unrelated screenshots
    on the public internet as a side effect of wanting one banner.
    """
    if not os.path.exists(OG_BANNER_PATH):
        raise HTTPException(status_code=404, detail="banner not committed")
    return FileResponse(OG_BANNER_PATH, media_type="image/png")


@app.get("/")
def index() -> FileResponse:
    """
    The page, served as the file it is committed as.

    One self-contained document: its stylesheet, its script and its two
    photographs are inside it, so the page a reader gets is the page in the
    repository, byte for byte, and there is no build step between the two. It
    is served rather than generated because a template that assembles HTML in
    Python is a second place for the page to be edited, and the two drift.

    Its numbers come from the endpoints below it at run time. Nothing on the
    page is computed here.
    """
    if not os.path.exists(INDEX_PATH):
        raise HTTPException(status_code=404, detail="page not committed")
    return FileResponse(INDEX_PATH, media_type="text/html; charset=utf-8")
