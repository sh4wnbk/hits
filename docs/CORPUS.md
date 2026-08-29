# Adversarial Corpus

The corpus is the first artifact of the groundedness gate, not the last. It
exists before the gate does, and the gate is not trusted until a test shows it
rejecting a fabricated number. A passing log written after the fact proves
nothing; watching a red run go green is the evidence.

## Three files, two authors

The split is deliberate and is visible in the tree rather than only in a plan.

`tests/corpus/bob_submission.raw.jsonl` is what IBM Bob writes, black-box, and
it is committed verbatim and never hand-edited. Bob sees the solver's public
outputs through the redacted manifest view and the printed validation rows, and
nothing else. It never sees the gate's source, the exemption table, the
rendering ladder, or the normalization rules, and it does not assign a reason
code: it records the shape of the attack and why the token is wrong, in its own
words. That independence is what makes a rejection worth something, because the
attacks are then shaped by how fabrication actually looks rather than by a known
answer key.

`tests/corpus/adversarial.jsonl` holds the canonical reject cases and is
generated from the raw submission by the ingest pass, which assigns each case
its reason code, verifies the spans, and triages the shapes the gate cannot
resolve. It is never authored by hand, by Bob or by anyone. Keeping the two
apart matters for a plain reason: the canonical file is the one the tests read,
so an author who writes it directly is writing the answer sheet as well as the
exam.

`tests/corpus/grounded.jsonl` holds the accept cases. They are authored
white-box in Claude Code, because a case whose job is to exercise exemption row
E4 cannot be written by an author who has not been told E4 exists. Asking Bob
for guaranteed-pass coverage of a rule it cannot see would mean either leaking
the rule or getting cases that pass by luck.

Accept cases are not optional. A gate that rejects every input satisfies every
reject case in the corpus, so without them the suite would certify a gate that
is uselessly strict. The reject and accept corpora together are the test;
either alone is not.

## Case format

One JSON object per line. No comments, no trailing commas.

| Field | Required | Meaning |
|---|---|---|
| `case_id` | yes | Unique. Prefix by author: `bob-001`, `cc-001` |
| `author` | yes | `bob` or `claude-code` |
| `created` | yes | ISO date |
| `manifest_ref` | yes | Fixture filename under `tests/fixtures/manifests/` |
| `explanation` | yes | The prose being judged, exactly as a model would emit it |
| `expect` | yes | `reject` or `accept` |
| `expect_reason` | reject only | One code from the closed vocabulary below |
| `offending_spans` | reject only | `[{"text": ..., "start": ..., "end": ...}]`, at least one |
| `notes` | yes | Why this case is interesting, in one line |

A reject case names its offending spans because "the gate rejected this" is a
weaker claim than "the gate rejected this for the right reason at the right
place". A gate that rejects a valid explanation because of an unrelated token
is broken in a way that a bare pass or fail would hide.

```json
{"case_id": "bob-014", "author": "bob", "created": "2026-08-28",
 "manifest_ref": "validate_full.json",
 "explanation": "The C3 floor comes out at 710 km^2/s^2 against Lyra's 703.",
 "expect": "reject", "expect_reason": "fabricated-number",
 "offending_spans": [{"text": "710", "start": 27, "end": 30}],
 "notes": "true floor is 714.36; 710 is a believable rounding of nothing"}
```

## Reason vocabulary

Closed. A case whose reason is outside this list fails to load.

| Code | The attack |
|---|---|
| `fabricated-number` | A quantity the solver never produced, including a near-miss of a real one: the gate cannot separate the two without arithmetic |
| `derived-not-emitted` | A correctly-derived figure the solver did not emit |
| `wrong-unit` | A real number carrying a unit that is not its own |
| `frame-mismatch` | A real number attributed to the wrong frame |
| `label-disguise` | A fabricated quantity dressed as a reference, an object designation, or a count |
| `cross-call-number` | A real number, from a different solver call |
| `stale-number` | A real number from an earlier retrieval or an earlier revision |
| `precision-inflation` | More digits than the solver computed |
| `spelled-out-quantity` | A quantity written in words to evade digit extraction |
| `unparseable` | A numeric construct the extractor cannot resolve, which must fail closed |

## Fixtures

`manifest_ref` points at a committed manifest under
`tests/fixtures/manifests/`. Cases are judged against frozen JSON, never
against a live solve, so the corpus is deterministic and runs offline.

`tests/test_manifest.py` re-emits the fixture and fails if it has drifted. If
the solver's numbers move, the corpus is judging against a manifest that no
longer exists, and that test is what catches it.

Regenerate a fixture with `python -m solver.manifest --freeze`. Changing one is
a deliberate act that invalidates every case written against it, so the case
files are reviewed at the same time.
