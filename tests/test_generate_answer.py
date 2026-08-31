"""
tests/test_generate_answer.py — the generation script's decisions, driven by a stub.

The script itself is run by a person and spends quota. What it decides, though,
is testable without spending any: whether a run gets written, and whether a run
that should not be written leaves anything behind.

That second question is the one worth a test. A floored run writing a file is
not a visible failure at the terminal, it is a file in data/answers/ that looks
exactly like a watched Granite generation and gets committed by the next
`git add -A`. CLAUDE.md is explicit that an offline result must never be
mis-credited to the credentialed system, and this is the shape that mistake
would actually take here.

No credential is read and no call is made: the client is a stub, injected the
same way the rest of the agent suite injects one.
"""

import importlib.util
import json
import os
from pathlib import Path

import pytest

from solver.frozen import load

SCRIPT = Path(__file__).resolve().parent.parent / "data" / "generate_answer.py"


def _module():
    spec = importlib.util.spec_from_file_location("generate_answer", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubClient:
    """Returns a fixed string. Never touches the network."""
    model_id = "ibm/granite-4-h-small"

    def __init__(self, text):
        self._text = text
        self.calls = 0

    def generate(self, prompt, system=""):
        self.calls += 1
        return self._text


@pytest.fixture
def mod():
    return _module()


def _grounded_text(key):
    """The floor's own prose, which is grounded by construction."""
    from agent.template import explain as floor
    return floor(load(key).manifest)


# ---------------------------------------------------------------------------
# The write decision
# ---------------------------------------------------------------------------

def test_a_grounded_granite_answer_is_written(mod, tmp_path, monkeypatch):
    stub = StubClient(_grounded_text("oumuamua"))
    monkeypatch.setattr(mod.granite, "from_env", lambda: stub)
    written = {}
    monkeypatch.setattr(mod, "save",
                        lambda a: written.setdefault("a", a) and None or "path")

    assert mod.generate("oumuamua") == 0
    assert stub.calls == 1

    a = written["a"]
    assert a.object_key == "oumuamua"
    assert a.served_by == "granite_first_pass"
    assert a.model_id == "ibm/granite-4-h-small"
    assert a.verified_grounded is True
    assert a.call_id == load("oumuamua").call_id
    assert a.verification_status == load("oumuamua").verification_status
    assert a.generated_at.endswith("Z")


def test_a_floored_run_writes_nothing_and_exits_nonzero(mod, tmp_path, monkeypatch):
    """
    The failure that would otherwise leave a committable artefact. The stub
    fabricates a number, the gate rejects it every time, the loop exhausts its
    retries and serves the floor, and the script must write nothing at all.
    """
    stub = StubClient("The departure energy is 99999.99 km^2/s^2 and nothing else.")
    monkeypatch.setattr(mod.granite, "from_env", lambda: stub)
    calls = []
    monkeypatch.setattr(mod, "save", lambda a: calls.append(a))

    assert mod.generate("borisov") == 1
    assert calls == [], "a floored run wrote a file"


def test_absent_credentials_are_an_error_not_a_floor(mod, monkeypatch):
    """
    Inverted from the rest of HITS on purpose. Everywhere else no credential is
    an ordinary outcome; here it means the one thing the script exists to do
    did not happen.
    """
    monkeypatch.setattr(mod.granite, "from_env", lambda: None)
    calls = []
    monkeypatch.setattr(mod, "save", lambda a: calls.append(a))

    assert mod.generate("atlas") == 1
    assert calls == []


def test_a_key_outside_the_committed_set_is_refused(mod, monkeypatch):
    called = []
    monkeypatch.setattr(mod.granite, "from_env",
                        lambda: called.append("from_env") or None)
    assert mod.generate("2I/Borisov") == 1
    assert called == [], "the key was validated after the client was built"


def test_usage_without_an_argument(mod):
    assert mod.main(["generate_answer.py"]) == 2
    assert mod.main(["generate_answer.py", "a", "b"]) == 2


# ---------------------------------------------------------------------------
# What the script may not do
# ---------------------------------------------------------------------------

def test_the_script_reads_no_credential_itself():
    """
    agent/granite.py is the only place a credential is read. A script that
    reached into os.environ for a key could also print it.
    """
    import ast
    tree = ast.parse(SCRIPT.read_text())
    reads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv")]
    assert not reads


def test_the_script_imports_no_solver_stack():
    """
    It loads a committed manifest, so it has no reason to import the solver.
    Keeping it light also keeps it runnable anywhere the service runs.
    """
    import ast
    tree = ast.parse(SCRIPT.read_text())
    names = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            names.append(n.module)
    for bad in ("numpy", "astropy", "hapsira", "scipy",
                "solver.intercept", "solver.solve", "solver.validate"):
        assert not any(x == bad or x.startswith(bad + ".") for x in names), bad
