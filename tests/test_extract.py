"""
tests/test_extract.py — the quantity-versus-incidental rule.

The rule is what stops the gate being either useless or unusable. Ground
nothing that looks like a label and a fabricated delta-v walks through wearing
"eq."; ground every numeral and the gate rejects "2 samples" and nobody keeps
it switched on.

Each exemption row is exercised on the corpus case that justifies it, and the
override is tested against the disguises it exists to defeat.
"""

import json
import os

import pytest

from verify.extract import extract, citable, Token
from verify.exemptions import EXEMPTION_ROWS

CORPUS = os.path.join(os.path.dirname(__file__), "corpus")


def _cases(name):
    with open(os.path.join(CORPUS, name), encoding="utf-8") as fh:
        return {json.loads(l)["case_id"]: json.loads(l) for l in fh if l.strip()}


@pytest.fixture(scope="module")
def accepts():
    return _cases("grounded.jsonl")


@pytest.fixture(scope="module")
def rejects():
    return _cases("adversarial.jsonl")


def _classified(text):
    return {t.text: t.classification for t in extract(text)}


# ---------------------------------------------------------------------------
# Clause 1: the override, which runs first
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,token", [
    ("eq. 4 gives 4.2 km/s", "4.2"),               # unit beats the reference row
    ("a delta-v of 4 was required", "4"),          # quantity noun beats a bare count
    ("computed 26.3 against 26.33", "26.33"),      # comparison marker
    ("the tolerance was 20", "20"),                # quantity noun, no unit
])
def test_clause_1_makes_unit_bearing_tokens_citable(text, token):
    assert _classified(text)[token] == "citable"


def test_a_reference_row_cannot_rescue_a_measurement():
    """
    The disguise the mandate names. "eq. 4" is a reference; a number beside a
    unit is a measurement however it is introduced.
    """
    got = _classified("per eq. 4 the excess is 4.2 km/s")
    assert got["4"] == "reference"      # the reference itself
    assert got["4.2"] == "citable"      # the measurement beside it


# ---------------------------------------------------------------------------
# Clause 2: every row, on the case that justifies it
# ---------------------------------------------------------------------------

def test_every_exemption_row_names_a_corpus_case():
    for row in EXEMPTION_ROWS:
        assert row.corpus_case, f"{row.id} has no justifying case"
        assert row.anchor, f"{row.id} has no non-numeric anchor"


def test_E1_designation_is_never_a_quantity(accepts):
    """
    1I is an object, not the number one. Enforced upstream by the tokenizer,
    which refuses a digit fused to a word character, so the assertion is on the
    outcome rather than on the row firing.
    """
    toks = extract(accepts["cc-004"]["explanation"])
    assert not any(t.text == "1" for t in toks)
    assert {t.text for t in citable(toks)} == {"26.28614", "714.36"}


def test_E2_routes_references_to_the_citation_check(accepts):
    toks = extract(accepts["cc-003"]["explanation"])
    refs = {t.text for t in toks if t.classification == "reference"}
    assert refs == {"4", "5", "6"}          # eq. 4, Fig. 5, Fig. 6
    assert "13.6" in {t.text for t in citable(toks)}


def test_E4_small_counts(accepts):
    toks = extract(accepts["cc-005"]["explanation"])
    assert ("2", "incidental") in {(t.text, t.classification) for t in toks}


def test_E5_list_markers(accepts):
    toks = extract(accepts["cc-006"]["explanation"])
    markers = {t.text for t in toks if t.rule == "E5"}
    assert markers == {"1", "2", "3"}


def test_E6_version_strings_and_identifiers(accepts):
    toks = extract(accepts["cc-007"]["explanation"])
    assert ("0.18", "incidental") in {(t.text, t.classification) for t in toks}
    assert not any("2000" in t.text for t in toks)   # ECLIPJ2000, J2000


def test_there_is_no_year_exemption():
    """
    docs/MANIFEST.md: years are entries, not exemptions. "Arrives in 2050" has
    to be groundable, or it cannot fail.
    """
    assert not any(r.id == "E3" for r in EXEMPTION_ROWS)
    assert _classified("the probe arrives in 2050")["2050"] == "citable"


# ---------------------------------------------------------------------------
# Clause 3: fail closed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id,expected", [
    ("bob-020", "twenty-seven"),
    ("bob-024", "thirteen point six"),
])
def test_spelled_out_quantities_are_caught(rejects, case_id, expected):
    """
    A number written as words beside a unit or a quantity noun is a measurement
    keeping itself out of digits. Reported, not skipped: skipping is how a
    fabricated figure evades the gate by being unreadable.
    """
    toks = extract(rejects[case_id]["explanation"])
    spelled = [t for t in toks if t.classification == "spelled-out"]
    assert [t.text for t in spelled] == [expected]


def test_malformed_numerals_are_caught(rejects):
    toks = extract(rejects["bob-032"]["explanation"])
    assert [t.text for t in toks if t.classification == "malformed"] == ["26.28.614"]


def test_a_named_version_is_not_a_malformed_number():
    toks = extract("the Lambert solve runs through hapsira 0.18.0 on this host")
    assert not any(t.classification == "malformed" for t in toks)


def test_unclassifiable_defaults_to_citable():
    got = extract("the value 8823 appears")
    assert [(t.text, t.classification) for t in got] == [("8823", "citable")]


# ---------------------------------------------------------------------------
# The accept corpus
# ---------------------------------------------------------------------------

def test_every_citable_token_in_the_accept_corpus_is_groundable(accepts):
    """
    The precondition for the membership test. If extraction marks something
    citable that the manifest cannot carry, a correct explanation is rejected
    and the gate is wrong in the direction nobody notices.
    """
    from solver.manifest import Manifest
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "manifests",
                           "validate_full.json")
    with open(fixture, encoding="utf-8") as fh:
        index = Manifest.from_json(fh.read()).index()
    orphans = [(cid, t.text) for cid, c in accepts.items()
               for t in citable(extract(c["explanation"])) if t.text not in index]
    assert not orphans, f"citable but not in the manifest: {orphans}"
