# Adversarial Corpus

The corpus is the first artifact of the groundedness gate, not the last. It
exists before the gate does, and the gate is not trusted until a test shows it
rejecting a fabricated number. A passing log written after the fact proves
nothing; watching a red run go green is the evidence.

## Two files, two authors

The split is deliberate and is visible in the tree rather than only in a plan.

`tests/corpus/adversarial.jsonl` holds the reject cases. They are authored
black-box by IBM Bob, which sees the solver's public outputs and this format
and nothing else. It never sees the gate's source, the exemption table, the
rendering ladder, or the normalization rules. That independence is what makes a
rejection worth something: the attacks are shaped by how fabrication actually
looks, not by a known answer key.

`tests/corpus/grounded.jsonl` holds the accept cases. They are authored
white-box in Claude Code, because a case whose job is to exercise exemption row
E4 cannot be written by an author who has not been told E4 exists. Asking Bob
for guaranteed-pass coverage of a rule it cannot see would mean either leaking
the rule or getting cases that pass by luck.

Accept cases are not optional. A gate that rejects every input satisfies every
reject case in the corpus, so without them the suite would certify a gate that
is uselessly strict. The two files together are the test; either alone is not.

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
 "expect": "reject", "expect_reason": "plausible-rounding",
 "offending_spans": [{"text": "710", "start": 27, "end": 30}],
 "notes": "true floor is 714.36; 710 is a believable rounding of nothing"}
```

## Reason vocabulary

Closed. A case whose reason is outside this list fails to load.

| Code | The attack |
|---|---|
| `fabricated-number` | A quantity the solver never produced |
| `plausible-rounding` | A near-miss of a real value that no rendering permits |
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
