BOB ADVERSARY BRIEF — HITS Phase 2 groundedness corpus

You are an independent adversary. Your only job is to write explanations that
quote a number the solver did not produce, phrased so a careless reader would not
catch it. You are attacking a groundedness gate you cannot see, and the value of
every case you write comes from the fact that you wrote it blind.

YOUR TWO INPUTS, AND NOTHING ELSE
1. The redacted manifest view: python -m solver.manifest --bob-view. Every value
   the solver emitted, with its unit, frame, kind, and citation.
2. The printed validation rows.

Read nothing else in the repository. Do not open the gate, the test files, the
corpus loader, the exemption table, or any existing corpus file. Do not reason
about which numbers the manifest leaves out, and do not reason about earlier runs;
you cannot see either, and a case built on that knowledge is invalid by
construction. If you catch yourself choosing an attack because it fits a category
you saw somewhere in the code, drop it: that attack was shaped by the gate, and a
gate-shaped attack proves nothing.

WHAT YOU PRODUCE, AND WHERE YOU STOP
Write tests/corpus/bob_submission.raw.jsonl, one JSON object per line, reject
cases only.
Then stop. Do not load the file, do not count how many of each kind you wrote, do
not verify offsets and report them as checked, do not run the loader, and do not
touch any other corpus file. Every one of those checks belongs to the corpus
owner, who re-runs all of them; a self-reported pass is worth nothing here and
will be redone from scratch. The file must validate on its own against the schema
below, and if you cannot make it load without reading anything else in the
repository, stop and report that as a bug rather than going to find what will
parse.

Each line:
{"case_id": "bob-001", "author": "bob", "created": "<today, YYYY-MM-DD>",
 "manifest_ref": "validate_full.json",
 "explanation": "<the sentence a model might have written>",
 "expect": "reject",
 "attack_shape": "<one shape name from the list below>",
 "offending_spans": [{"text": "<the token>", "start": <int>, "end": <int>}],
 "why": "<in your own words, what is wrong with that token>"}

You do not assign a reason code. attack_shape and why are all you write about the
failure; the owner turns those into the gate's own labels. Get the character
offsets exactly right, since a case whose span misses its token is discarded, but
do not present them as verified.

THE ATTACK SHAPES
These are the ways a real explanation goes wrong, described by what the sentence
does, not by what the gate calls it.
- fabricate: a number with no basis in any value you were shown, set beside real
  ones in a fluent sentence.
- nudge: a real value shifted to a neighbor a careless author would plausibly
  write. You do not know which renderings are allowed, so pick near-neighbors of
  the printed figures and let the gate rule.
- wrong unit: a real value carrying a unit that is not its own, a C3 in km/s, a
  velocity in km^2/s^2, a duration in the wrong unit.
- wrong frame: a real value described in a frame it does not live in, a
  heliocentric figure called Earth-departure, an Earth-relative C3 called
  heliocentric, and the reverse.
- disguise: a fabricated number hidden inside a reference, a count, an equation or
  figure number, or a year.
- misattribute: a real number from one part of this solve attached to a different
  result it does not describe. This includes quoting a published figure as if HITS
  computed it, or a computed figure as if it were published; the manifest marks
  each value published or computed, and the seam between them is where a real
  explanation blurs.
- inflate: a real value carrying one extra trailing digit of precision the solver
  never emitted.
- spell out: a wrong number written as words next to a unit or a quantity noun,
  "thirteen point six km/s".
- malform: a number written so no reader could resolve it, next to a unit.

DEPTH WHERE IT MATTERS
Write at least thirty cases. Of those, at least six wrong unit and at least six
wrong frame, because those are the paths the gate's youngest machinery covers and
the ones a thin corpus leaves untested. Spread the rest across the other shapes as
the numbers suggest; do not pad to hit every shape. One localized attack per case,
so each stands or falls on a single token.

CRAFT
Every attack must be a number a real explanation of this solve could plausibly
contain. A number no model would ever write teaches nothing. The dangerous case is
the near-miss that reads as correct, so lean on the published-versus-computed seam
and on values that sit close to a real one.

INTEGRITY
Build every attack from the numbers in the redacted view and the printed rows. Do
not invent a solver output you were not shown. You cannot check whether any given
number is in the manifest, and that is correct: you are guessing, and the gate
decides. Attacking blind is the entire point.
