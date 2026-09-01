# Generations, 2026-08-31

The raw Granite output behind the Phase 3 rows in `docs/BOB_USAGE.md` and the
"Where the AI can fall short" list in the README.

Those two documents say what the model got wrong. This directory is the
evidence for it. Without these files a reader has the project's word that
Granite called an interstellar object a planet and invented a source paper,
which is exactly the kind of claim this repository is built not to ask anyone
to take on trust.

## What these are not

**None of these is a served answer.** The answers HITS serves are in
`data/answers/`, all three are the deterministic template, and every one is
re-gated against its manifest by `tests/test_answers.py`. Nothing here is
gated, nothing here is served, and nothing here should be copied into
`data/answers/`.

The filenames are deliberately not `{key}.json`. The set of servable answers is
closed to the three object keys, and
`test_the_answer_directory_holds_nothing_but_the_closed_set` fails on any file
in `data/answers/` outside it, so a stray copy of one of these is caught rather
than served. They keep the `CachedAnswer` schema so they can be read by the
same code that reads a real one, which is the only reason they are json.

## The files

| File | served_by | Verdict | What it shows |
|---|---|---|---|
| `2026-08-31-borisov-target-planet.json` | `granite_first_pass` | grounded | Calls 2I/Borisov "a target planet", three times. Every figure came from the manifest and the gate passed it: it checks numbers, and this is a noun. The prompt had never said what the object was. |
| `2026-08-31-borisov-could-intercept.json` | `granite_after_regen` | grounded | The object named correctly, no invented source, and it still says "a spacecraft could intercept". HITS models no launch vehicle and cannot make that claim. |
| `2026-08-31-borisov-source-paper.json` | `granite_first_pass` | grounded | Credits a computed figure to "the source paper". No published intercept study of Borisov exists; that absence is the whole content of its verification status. This one motivated the `unsourced-attribution` rule, and is now rejected by it. |
| `2026-08-31-oumuamua-could-reach.json` | `granite_first_pass` | grounded | Clean on the object, the source and the figures, and says "a spacecraft could reach". The fourth feasibility claim of the evening. |

`rejected-attempts.md` holds the drafts the gate refused, transcribed from run
output because they never became files, including all three 3I/ATLAS attempts
and the attempt where the `unsourced-attribution` rule fired live.

## Re-checking them

Every file here still answers to the gate. The first three are grounded and the
point is that grounded was not enough:

```bash
python - <<'PY'
import json, glob
from solver.frozen import load
from verify.groundedness import check
for path in sorted(glob.glob("docs/generations/*.json")):
    d = json.load(open(path))
    v = check(d["text"], load(d["object_key"]).manifest)
    print(f"{path}: grounded={v.grounded} {[(f.text, f.reason) for f in v.findings]}")
PY
```

`2026-08-31-borisov-source-paper.json` now comes back **not** grounded, on
`unsourced-attribution`, because the rule it prompted did not exist when it was
generated. That difference is the record of the gate getting stricter, and it
is worth running rather than reading.

## Why all three objects ship the template

Granite was not unavailable. It answered every time it was asked, six live
calls, and four of the answers grounded. Every grounded one claimed the mission
could be flown, which is a judgement HITS has no launcher model to make and the
gate has no way to see. The answers were read and the template was shipped
instead. That is a person catching something the system could not, and the
files here are what they were reading.
