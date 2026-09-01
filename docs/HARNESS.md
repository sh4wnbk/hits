# Harness

How this project was built and what that buys a reader. It is the process
record, not a second architecture document: what tool wrote which layer, what
had to go red before anything was believed, which invariants a machine checks
rather than a person, and where the checking stops.

Every claim here names the file or test it rests on. Where the enforcement is
a person rather than a program, it says so.

## Two tools, one committer

IBM Bob was the primary development tool for Phase 1, the part of this
repository that computes. Across three sessions on 2026-08-27, logged step by
step in `BOB_USAGE.md`, Bob built the dependency baseline, the Horizons
fetch and the committed state vectors, the Lambert wrapper over hyperbolic
targets, the solve and grid surface, the validation suite against Hein et al.
2019, and the C3 porkchop slice. It then produced the Phase 2 adversarial
corpus, 35 reject cases written black-box, committed verbatim as
`tests/corpus/bob_submission.raw.jsonl`.

Claude Code took over at the Phase 1/2 boundary and built the layer that
interprets: the manifest emitter, the groundedness gate, the corpus ingest,
the deterministic explanation floor, and the generate-and-gate loop. The
handoff is recorded at the boundary rather than reconstructed after it, in the Phase 2
tool-handoff entry of `BOB_USAGE.md`.

Every commit in this repository is authored by one human committer. Git
carries no tool authorship and cannot be made to carry it retroactively, so
the Bob-primary claim rests on `BOB_USAGE.md` as a session log written as
the work happened. That is a weaker form of evidence than a signature and a
stronger one than a claim made at submission time, and it is stated this way
because the alternative, backfilling authorship into commit metadata, would be
a fabrication of exactly the kind this project's gate exists to catch.

## Failing case first

Nothing here is believed because the reasoning about it sounded right.
CLAUDE.md is explicit that an explanation of what the code does is a
hypothesis until executed, and that on a prior project an assistant reasoned
its way to a bug that did not exist. So each layer was built against a check
that was red first.

The corpus and its runner exist before the gate does. `tests/test_groundedness.py`
was committed while `verify/groundedness.py` did not exist, its module docstring
saying the expected state of the file on that commit is red, and the Phase 2
log records the run: 16 failed, 3 passed. The gate was then written until those
same tests went green without being edited.

The deterministic floor was built and gated before the fallible path that
leans on it. `agent/template.py` and its tests landed in commit c684472,
`agent/explain.py` in 7378e8f, so the fallback existed and was proven grounded
before anything could fall back to it.

The dogfood test in `tests/test_groundedness.py` is the most recent instance
and the clearest. `docs/MANIFEST.md` claimed the printed validation rows were
bound to the manifest and that a test enforced it. The test did not exist.
Writing it turned it red: the C3 gap-attribution row was printing a full
`retrieved_utc` timestamp, and the minutes field was a number no manifest entry
carried.

## Watched, not logged

A passing log written after the fact proves nothing, which is why
`docs/CORPUS.md` puts the standard as watching a red run go green.

`tests/test_explain_proof.py` is that standard applied to the central
invariant. A stub that fabricates a different number on every call is watched
being caught three times and never reaching the output
(`test_fabricating_on_every_call_falls_to_the_floor`); a stub grounded on the
first try is credited to `granite_first_pass`; one grounded only on the last
retry is credited to `granite_after_regen`, so the three exits are told apart
by demonstration rather than by inspection. The suite drives every path with a
stub and never calls watsonx.

The live run of 2026-08-30 is reported separately for the same reason. What
the stubbed suite proves is the loop's behaviour whatever the model returns.
What the live run proves is that the endpoint works, and it is logged as its
own rows rather than folded into the stub result.

## The corpus boundary

The reject cases are worth something only if their author could not see the
answer key, so the independence is structural rather than promised.

Bob wrote against `BOB_BRIEF_CORPUS.md`, seeing the solver's public
outputs through the redacted manifest view and the printed validation rows,
and never the gate's source, the exemption table, the rendering ladder, or the
normalization rules. Three files keep that boundary visible in the tree:
`tests/corpus/bob_submission.raw.jsonl` is Bob's, committed verbatim and never hand-edited;
`tests/corpus/adversarial.jsonl` is generated from it by `verify/corpus_ingest.py`, which
assigns each reason code and verifies each span; `tests/corpus/grounded.jsonl` holds the
accept cases, authored white-box, because a case whose job is to exercise a
named exemption row cannot be written by an author who has not been told the
row exists.

The boundary is enforced by the raw loader rather than by discipline.
`tests/test_corpus_raw.py` proves that a submission is refused if it assigns
its own reason code, carries a field the brief never asked for, names an
author other than Bob, contains an accept case, or ships a span whose offsets
do not land on the token it names. A contaminated submission fails to load
rather than quietly entering the corpus.

Bob's 35 cases resolved into 30 canonical rejections, 2 accepted limits, and 3
quarantined with their reasons recorded. Nothing was deleted: a case removed
without a trace would make the corpus unfalsifiable.

## What a machine checks

These are the invariants no reviewer has to hold in their head. Each is a test
in the suite, and each fails the run rather than producing a warning.

| Invariant | Test | What it walks |
|---|---|---|
| The gate does no arithmetic | `test_gate_does_no_arithmetic` | The AST of `verify/groundedness.py`, rejecting arithmetic operators, `float`/`round`/`abs`/`int`, and any import of math, numpy, decimal, fractions or statistics |
| The floor formats no number | `test_template_never_formats_a_number` | The AST of `agent/template.py`, rejecting format specifiers, rounding calls, arithmetic and numeric literals |
| Every number in the floor is a manifest rendering | `test_every_number_in_the_floor_is_a_manifest_rendering` | The floor's own output, token by token |
| The manifest is complete | `test_every_float_of_every_public_result_is_in_the_manifest` | Reflection over every public result dataclass, so a new solver field cannot be added without becoming citable |
| The ladders are pinned | `test_pinned_ladders`, `test_ladder_excludes_the_near_misses_it_is_meant_to` | The declared renderings, so the gate never rounds and a near-miss never enters by accident |
| The fixture has not drifted | `test_frozen_fixture_matches_freshly_emitted_manifest` | A freshly emitted manifest against the committed one |
| The printed rows are grounded | `test_the_printed_validation_rows_are_grounded` | The gate over the solver's own printed validation output |

The reflection test is the one that matters most over time. Membership is only
as good as the manifest's coverage, so a check that a person must remember to
extend is a check that decays; walking the dataclasses means the manifest
grows when the solver does or the build goes red.

Two of these deserve their real status rather than their nice-sounding one.
The AST tests prove the modules contain no arithmetic and no format specifier,
which is a property of the source text. They do not prove the gate's logic is
correct, and nothing here does; that is what the corpus is for.

## Where the enforcement actually is

`.github/workflows/ci.yml` runs the full suite on every push to main and every
pull request, so the guardrails above have a trigger that is not a person
remembering. It installs the pinned set, refuses a tracked `.env`, and runs
`pytest` with no secrets configured, which is also what proves the
credential-free claim: if anything in `solver/` or `verify/` reached for a
secret, the run would fail rather than quietly pass on a developer's machine
that happens to have one.

The workflow was verified before it was described here, by installing into a
clean virtual environment exactly as the workflow does and running the suite
there: 192 passed, 1 skipped, 1 xfailed. That check earned its keep
immediately. `pip install -r requirements.txt` could not succeed on a clean
Python 3.12 at all, because the freeze pinned `matplotlib==3.7.2`, which has
no CPython 3.12 wheel, while hapsira caps matplotlib below 3.8 and every
installable version under that cap requires NumPy 1. The pin came from a
development host where matplotlib had been built by other means. HITS never
imports it, so it is out of the file and the install is `--no-deps`.

What CI still does not gate is the credentialed half. No watsonx call and no
Horizons call happens in a CI run, so the live Granite path is proven by dated
runs in `BOB_USAGE.md` and never by a green build. Nor does anything
check documents against the module tree: this file, and every other, is
maintained by hand, which is why they carry explicit unbuilt markers rather
than relying on a reader to notice.

## What the harness does not catch

Four limits, stated here rather than only in the documents that own them,
because a process record that lists its guardrails without their gaps is
advertising.

**Two attribution cases the gate cannot see.** A real number attached to the
wrong result, in the right unit and the right frame, passes. The C3 floor
departure date given as the grid window's start date is the shape of it. Cases
bob-027 and bob-033 sit in `tests/corpus/known_limits.jsonl` as accepted
limits rather than being counted as catches, because which result a number
describes is not encoded in any manifest metadata. The published-versus-computed
half of misattribution IS caught, since provenance is metadata, and that half
moved seven cases back into the rejection count when `check_attribution`
landed.

**The gate cannot say what kind of wrong a number is.** A plausible rounding, a
correct derivation the manifest never emitted, a value from an earlier
retrieval, and an outright invention all arrive as a string the index does not
hold. Telling them apart means comparing magnitudes, which is the arithmetic
the no-arithmetic rule forbids, so all four are rejected identically as
`fabricated-number`. This is the price of the guarantee rather than an
oversight: a gate that measured how close a wrong number was would be
certifying its own arithmetic instead of the explanation's grounding.
`docs/MANIFEST.md` argues it in full.

**Grounded is not correct.** The gate checks where a number came from, not
whether the sentence around it is true. The first live explanation, on
2026-08-30, carried only manifest renderings and still said the 2027 C3
comparison "exceeds the solver's tolerance of 20%" when 4.92% is inside it.
Membership and attribution have nothing to say about a comparative assertion,
and the manifest carries no pass/fail entry the model could have quoted
instead of reasoning its way to one. A grounded explanation must not be
described as a correct one.

**Granite Guardian is not wired in.** Every verdict reports its advisory field
as `unavailable`. The deterministic comparison is dispositive and is running;
the second opinion is not.
