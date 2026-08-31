"""
tests/test_serve_imports.py — the deployed process stays light.

app/main.py answers questions about orbital transfers without importing an
orbital-mechanics library. That is not an optimisation. CLAUDE.md makes
accessibility a design gate, and the deployment that satisfies it is a free
instance with a few hundred megabytes of memory and a build that finishes; the
scientific stack fits in neither. The numbers were computed at build time and
committed, so serving them is a json read.

The failure this guards against is quiet. Someone adds `from solver.intercept
import intercept` to a handler, every test still passes locally where the stack
is installed, and the deploy dies on a machine nobody is watching. So the check
runs in a subprocess: this suite imports the solver, and an in-process
assertion would be reading a sys.modules that numpy entered hours ago.
"""

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAVY = ("numpy", "astropy", "hapsira", "scipy")

# Serving dependencies, skipped rather than failed where only the solver stack
# is installed. The solver suite has to stay runnable without them: they are in
# requirements-serve.txt precisely because they are not solver dependencies.
pytest.importorskip("fastapi", reason="serving dependency, not a solver one")
pytest.importorskip("httpx2", reason="fastapi.testclient needs it")

from fastapi.testclient import TestClient          # noqa: E402

from app.main import app                            # noqa: E402
from solver import objects                          # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Import weight
# ---------------------------------------------------------------------------

PROBE = """
import sys, json
import app.main
heavy = sorted({m.split('.')[0] for m in sys.modules if m.split('.')[0] in %r})
print(json.dumps({"heavy": heavy, "n_modules": len(sys.modules)}))
""" % (HEAVY,)

SERVING_PROBE = """
import sys, json
from fastapi.testclient import TestClient
from app.main import app
from solver import objects

c = TestClient(app)
codes = [c.get("/health").status_code, c.get("/objects").status_code]
served = []
for k in objects.KEYS:
    r = c.get("/explain/" + k)
    codes.append(r.status_code)
    served.append(r.json()["served_by"])

heavy = sorted({m.split('.')[0] for m in sys.modules if m.split('.')[0] in %r})
print(json.dumps({"heavy": heavy, "codes": codes, "served_by": served,
                  "n_modules": len(sys.modules)}))
""" % (HEAVY,)


def _run(source: str) -> dict:
    proc = subprocess.run([sys.executable, "-c", source],
                          cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"probe failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_importing_the_app_pulls_in_no_scientific_stack():
    out = _run(PROBE)
    assert out["heavy"] == [], (
        f"importing app.main pulled in {out['heavy']}. The deployed web "
        "process must import none of numpy, astropy, hapsira or scipy: they "
        "are not in requirements-serve.txt, so this is a deploy that fails "
        "at start rather than a test that is merely strict.")


def test_answering_every_object_pulls_in_no_scientific_stack():
    """
    The stronger form. Importing lightly proves little if the first request
    imports the solver lazily, so the probe actually serves all three objects
    and then looks.
    """
    out = _run(SERVING_PROBE)
    assert out["codes"] == [200] * 5, out["codes"]
    assert out["served_by"] == ["deterministic_floor"] * 3, out["served_by"]
    assert out["heavy"] == [], (
        f"serving pulled in {out['heavy']}, so a handler is reaching the "
        "solver at request time rather than reading a committed manifest.")


def test_requirements_serve_names_no_solver_dependency():
    """
    The file and the test say the same thing, so a dependency cannot be added
    to the deployment without this failing.
    """
    with open(os.path.join(REPO_ROOT, "requirements-serve.txt")) as fh:
        lines = [ln.strip().lower() for ln in fh
                 if ln.strip() and not ln.startswith("#")]
    named = {ln.split("==")[0].split("[")[0] for ln in lines}
    assert named == {"fastapi", "uvicorn", "requests"}, named
    for heavy in HEAVY + ("matplotlib", "astroquery"):
        assert heavy not in named


# ---------------------------------------------------------------------------
# The endpoints
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_objects_lists_three_with_their_verification_status(client):
    r = client.get("/objects")
    assert r.status_code == 200
    got = r.json()["objects"]
    assert [o["key"] for o in got] == list(objects.KEYS)

    by_key = {o["key"]: o for o in got}
    assert by_key["oumuamua"]["verification_status"] == objects.VALIDATED
    for key in ("borisov", "atlas"):
        assert by_key[key]["verification_status"] == objects.UNVALIDATED
        assert "no published intercept study" in by_key[key]["verification_status"]


def test_explain_serves_the_gated_floor_for_every_object(client):
    """
    Three grounded answers with no credential and no network. `served_by` is
    asserted alongside `grounded`, because CLAUDE.md forbids a no-credentials
    result being mis-credited to the credentialed system, and the field is
    where that is either kept or lost.
    """
    for key in objects.KEYS:
        r = client.get(f"/explain/{key}")
        assert r.status_code == 200
        body = r.json()
        assert body["object"] == key
        assert body["served_by"] == "deterministic_floor"
        assert body["floor_reason"] == "no watsonx credentials in the environment"
        assert body["grounded"] is True
        assert body["designation"] in body["text"]
        assert "patched-conic" in body["text"].lower()


def test_the_three_answers_are_distinct(client):
    """
    A shared flight time and a shared order of magnitude make it worth
    asserting that three requests are not returning one cached answer.
    """
    texts = {client.get(f"/explain/{k}").json()["text"] for k in objects.KEYS}
    call_ids = {client.get(f"/explain/{k}").json()["call_id"] for k in objects.KEYS}
    assert len(texts) == 3
    assert len(call_ids) == 3


def test_a_committed_answer_is_served_and_a_missing_one_falls_to_the_floor(
        client, monkeypatch):
    """
    The two branches of /explain, both of them, because the page depends on the
    fall-through and nothing exercised it.

    A frozen answer is served as it was frozen, `served_by` and `generated_at`
    carried from the file rather than recomputed, and `source` says `cached` so
    a reader can tell a watched generation from one made for them. With no file
    the request falls to the gated floor and says so. The cache is stubbed
    rather than written into data/answers/, so the test states the behaviour
    without depending on whether a generation has been run yet.
    """
    from app import answers as answer_store
    from app.main import answer_store as bound

    frozen = answer_store.CachedAnswer(
        object_key="oumuamua",
        text="Frozen prose, standing in for a watched generation.",
        served_by="granite_after_regen",
        model_id="ibm/granite-4-h-small",
        generated_at="2026-08-30T00:00:00Z",
        call_id="stub",
        verification_status=objects.VALIDATED,
        regenerations=1,
        verified_grounded=True,
    )
    monkeypatch.setattr(bound, "load", lambda key: frozen if key == "oumuamua" else None)

    hit = client.get("/explain/oumuamua").json()
    assert hit["source"] == "cached"
    assert hit["text"] == frozen.text
    assert hit["served_by"] == "granite_after_regen"
    assert hit["model_id"] == "ibm/granite-4-h-small"
    assert hit["generated_at"] == "2026-08-30T00:00:00Z"
    assert hit["regenerations"] == 1
    assert hit["grounded"] is True

    miss = client.get("/explain/borisov").json()
    assert miss["source"] == "live-no-cache"
    assert miss["served_by"] == "deterministic_floor"
    assert miss["floor_reason"] == "no watsonx credentials in the environment"
    assert miss["grounded"] is True


def test_an_unknown_target_is_404_and_names_the_closed_set(client):
    """
    A free-text designation is refused rather than resolved. The message hands
    back the three keys, which is the only useful thing to say to a caller who
    typed a designation instead of a key.
    """
    for bad in ["2I/Borisov", "1I", "oumuamua ", "C/2019 Q4", "..%2f..%2fetc"]:
        r = client.get(f"/explain/{bad}")
        assert r.status_code == 404, (bad, r.status_code)
        detail = r.json()["detail"]
        assert "free-text" in detail
        assert "oumuamua" in detail and "borisov" in detail and "atlas" in detail


def test_the_gate_demo_answers_a_browser_and_an_api_caller_from_one_url(client):
    """
    A reader following a link about honesty should not land on raw json, and a
    judge scripting the same URL should not have to parse HTML. So the format
    is negotiated: an explicit `?format=` wins, otherwise the Accept header
    decides, and a caller that expresses no preference gets the data. That last
    case is what keeps curl and every existing caller working unchanged.
    """
    data = client.get("/gate/demo/oumuamua")
    assert data.status_code == 200
    assert data.headers["content-type"].startswith("application/json")
    assert data.json()["injection"]["solver_value"]

    page = client.get("/gate/demo/oumuamua", headers={"accept": "text/html"})
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "<!DOCTYPE html>" in page.text

    # The two shapes are the same computation, and `?format=` overrides Accept
    # in both directions.
    forced_json = client.get("/gate/demo/oumuamua?format=json",
                             headers={"accept": "text/html"})
    assert forced_json.headers["content-type"].startswith("application/json")
    assert forced_json.json() == data.json()

    forced_html = client.get("/gate/demo/oumuamua?format=html")
    assert forced_html.headers["content-type"].startswith("text/html")
    assert forced_html.text == page.text

    bad = client.get("/gate/demo/oumuamua?format=xml")
    assert bad.status_code == 400

    # An unknown object is a 404 in either shape, rather than a page that
    # loads and then cannot fill itself in.
    for headers in ({}, {"accept": "text/html"}):
        r = client.get("/gate/demo/nonesuch", headers=headers)
        assert r.status_code == 404


def test_the_gate_view_writes_down_no_figure(client):
    """
    The readable view fetches its own numbers from `?format=json`, so the file
    holds none. The section it mirrors on the landing page is checked the same
    way by test_index_states_no_number, and for the same reason: an exhibit
    built to show that no number reaches a reader ungrounded cannot be the one
    place a number is typed in by hand.
    """
    page = client.get("/gate/demo/oumuamua", headers={"accept": "text/html"}).text
    demo = client.get("/gate/demo/oumuamua?format=json").json()
    assert demo["injection"]["solver_value"] not in page
    assert demo["injection"]["injected_token"] not in page
    for figure in ["393.34", "393.39", "1727.89", "2919.78", "19.8328", "13.96737"]:
        assert figure not in page


def test_index_states_no_number(client):
    """
    Every figure HITS shows is a gated one. A number written into the landing
    page template would be the first ungrounded number in the system, so the
    placeholder carries none.
    """
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Can we catch it?" in body
    assert "Hyperbolic Intercept" in body
    assert "github.com/sh4wnbk/hits" in body
    for figure in ["393.34", "1727.89", "2919.78", "19.8328", "13.96737", "7305"]:
        assert figure not in body
