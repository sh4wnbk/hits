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

import html
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

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

PAGE_CSS = """
:root { --ink:#16181d; --dim:#5b6270; --line:#dfe2e8; --bg:#fbfbfc;
        --card:#fff; --accent:#1a4fd8; --warn:#8a5a00; --warnbg:#fff8e6; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif; }
.wrap { max-width:52rem; margin:0 auto; padding:2rem 1.1rem 4rem; }
header { margin-bottom:1.5rem; }
h1 { font-size:1rem; font-weight:600; color:var(--dim); margin:0 0 .3rem;
     letter-spacing:.01em; }
.tagline { font-size:2rem; font-weight:700; margin:0 0 .6rem; }
.lede { color:var(--dim); margin:0 0 .5rem; max-width:42rem; }
h2 { font-size:1.05rem; margin:2rem 0 .3rem; }
.sub { color:var(--dim); font-size:.87rem; margin:0 0 .9rem; }
.cards { display:grid; gap:.9rem; grid-template-columns:repeat(auto-fit,minmax(15rem,1fr)); }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:.9rem; }
.card h3 { margin:0 0 .2rem; font-size:1.05rem; }
.vs { font-size:.8rem; color:var(--dim); margin:.35rem 0 .6rem; }
.vs.validated { color:#1a6b2f; }
button { font:inherit; cursor:pointer; background:var(--accent); color:#fff;
         border:0; border-radius:6px; padding:.45rem .8rem; }
button.ghost { background:#eef1f6; color:var(--ink); }
button[disabled] { opacity:.55; cursor:default; }
.chips { display:flex; flex-wrap:wrap; gap:.5rem; }
.chip { background:var(--card); border:1px solid var(--line); border-radius:999px;
        padding:.4rem .85rem; font-size:.9rem; cursor:pointer; text-align:left; color:var(--ink); }
.chip:hover { border-color:var(--accent); }
.facet { border:1px solid var(--line); border-radius:8px; background:var(--card);
         padding:.7rem .85rem; margin-bottom:.6rem; }
.facet .label { font-weight:600; }
.facet .ids { font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
              color:var(--dim); margin-top:.2rem; }
.prov { font-size:.82rem; color:var(--dim); margin-top:.4rem;
        border-left:3px solid var(--line); padding-left:.6rem; }
.note { font-size:.82rem; color:var(--warn); background:var(--warnbg);
        border-radius:5px; padding:.4rem .6rem; margin-top:.4rem; }
#out { margin-top:1rem; }
.answer { background:var(--card); border:1px solid var(--line); border-radius:8px;
          padding:1rem; white-space:pre-wrap; }
.meta { font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--dim);
        border-top:1px solid var(--line); margin-top:.8rem; padding-top:.6rem;
        white-space:pre-wrap; }
footer { margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line);
         color:var(--dim); font-size:.85rem; }
a { color:var(--accent); }
"""


def _page() -> str:
    """
    The chips page. Plain HTML, one inline stylesheet, one inline script.

    No framework and no build step, deliberately: the accessibility gate says a
    reader needs no setup, and it applies to the page's own delivery. There is
    also no number in this template. Every figure a reader sees arrives from
    /explain, which serves gated text and nothing else.
    """
    fis = [load(k) for k in objects.KEYS]
    cards = []
    for fi in fis:
        cached = answer_store.load(fi.key)
        cls = "vs validated" if fi.is_validated else "vs"
        badge = "cached" if cached else "live"
        cards.append(f"""
      <div class="card">
        <h3>{html.escape(fi.designation)}</h3>
        <div class="{cls}">{html.escape(fi.verification_status)}</div>
        <button onclick="ask('{fi.key}')">Can we catch it?</button>
        <button class="ghost" onclick="ask('{fi.key}',1)">Regenerate live</button>
        <div class="ids" style="margin-top:.4rem;font-size:11px;color:#5b6270">
          answer: {badge}</div>
      </div>""")

    facets = []
    for f in chips.OBJECT_FACETS:
        prov = ""
        if f.mined:
            prov = (f'<div class="prov">Asked as: &ldquo;{html.escape(f.mined)}'
                    f'&rdquo; <span style="opacity:.75">({html.escape(f.mined_source)})</span></div>')
        note = f'<div class="note">{html.escape(f.note)}</div>' if f.note else ""
        facets.append(f"""
      <div class="facet">
        <div class="label">{html.escape(f.label)}</div>
        <div class="ids">{html.escape(", ".join(f.entry_ids))}</div>
        {prov}{note}
      </div>""")

    ev = []
    for c in chips.EVIDENCE_CHIPS:
        ev.append(f'<button class="chip" onclick="eq(\'{c.eid}\')">'
                  f'{html.escape(c.label)}</button>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(TITLE)}</title>
<meta name="description" content="{html.escape(SUMMARY)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(TITLE)}">
<meta property="og:description" content="{html.escape(SUMMARY)}">
<meta property="og:image" content="{PUBLIC_URL}/static/og_banner.png">
<meta property="og:url" content="{PUBLIC_URL}/">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(TITLE)}">
<meta name="twitter:description" content="{html.escape(SUMMARY)}">
<meta name="twitter:image" content="{PUBLIC_URL}/static/og_banner.png">
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>{html.escape(TITLE)}</h1>
  <p class="tagline">{TAGLINE}</p>
  <p class="lede">{html.escape(SUMMARY)}</p>
</header>

<noscript>
  <div class="note" style="margin-bottom:1.5rem">
    <strong>This page uses JavaScript to fetch answers, and it is switched
    off.</strong> HITS computes what it would cost to send a probe to one of the
    three known interstellar objects: 1I/'Oumuamua, 2I/Borisov and 3I/ATLAS. A
    deterministic solver works out the trajectory, and every number in the
    written explanation is checked against the solver's own output before it is
    shown, so the explanation cannot contain a figure the solver did not
    produce. The answers are readable without JavaScript as plain JSON at
    <code>/explain/oumuamua</code>, <code>/explain/borisov</code> and
    <code>/explain/atlas</code>, the evidence answers at <code>/evidence/E1</code>
    through <code>/evidence/E4</code>, and the number check can be watched
    accepting a real figure and rejecting an invented one at
    <code>/gate/demo/oumuamua</code>. The source and the validation are at
    <a href="{REPO_URL}">{REPO_URL}</a>.
  </div>
</noscript>

<h2>The three interstellar objects</h2>
<p class="sub">Three, because three is how many humanity has found. Each card
says what backs its numbers.</p>
<div class="cards">{"".join(cards)}</div>

<div id="out"></div>

<h2>What an object answer covers</h2>
<p class="sub">{html.escape(chips.CORPUS_NOTE)}</p>
{"".join(facets)}

<h2>About the tool itself</h2>
<p class="sub">Answered from committed sources rather than computed, and each
answer names them.</p>
<div class="chips">{"".join(ev)}</div>

<footer>
  Patched-conic, two-body. HITS does not perform n-body integration and does not
  model non-gravitational forces. It reports what a transfer costs and does not
  model launch-vehicle capability, so it does not say whether a mission is
  flyable. &middot; <a href="{REPO_URL}">Source and validation</a>
</footer>
</div>

<script>
const out = document.getElementById('out');
function esc(s){{ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }}
function busy(m){{ out.innerHTML = '<div class="answer">'+esc(m)+'</div>'; }}

async function ask(key, live){{
  busy(live ? 'Calling Granite now. This can take a few seconds.' : 'Loading.');
  try {{
    const r = await fetch('/explain/'+key+(live?'?live=1':''));
    const d = await r.json();
    const meta = [
      'served_by:      '+d.served_by,
      'source:         '+d.source,
      'grounded:       '+d.grounded,
      'model_id:       '+(d.model_id || '(none)'),
      'generated_at:   '+(d.generated_at || '(this request)'),
      'regenerations:  '+d.regenerations,
      'guardian:       '+d.advisory,
      d.floor_reason ? 'floor_reason:   '+d.floor_reason : null,
      'verification:   '+d.verification_status
    ].filter(Boolean).join('\\n');
    out.innerHTML = '<div class="answer">'+esc(d.text)+
      '<div class="meta">'+esc(meta)+'</div></div>';
  }} catch(e) {{ busy('Request failed: '+e); }}
}}

async function eq(eid){{
  busy('Loading.');
  try {{
    const r = await fetch('/evidence/'+eid);
    if (!r.ok) {{ busy('Not answered yet.'); return; }}
    const d = await r.json();
    const meta = 'asked as:  "'+d.mined_from+'"  ('+d.mined_source+')\\n'+
                 'sources:   '+d.sources.join('\\n           ');
    out.innerHTML = '<div class="answer"><strong>'+esc(d.question)+'</strong>\\n\\n'+
      esc(d.text)+'<div class="meta">'+esc(meta)+'</div></div>';
  }} catch(e) {{ busy('Request failed: '+e); }}
}}
</script>
</body>
</html>
"""


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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _page()
