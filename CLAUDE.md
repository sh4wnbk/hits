# CLAUDE.md

Read this first. It primes a session on what HITS is, what it refuses to do,
and how work here is judged.

## What HITS is

HITS is an accessibility layer over NASA data services that answers one
question about an interstellar object: could we send a probe to it?

Deterministic orbital mechanics computes the answer. A Granite agent
interprets it. The tool is reachable at one URL with no setup.

It is not a general mission-design environment, and not a competitor to GMAT.
It answers one question well.

## Three-question test for new components

Before building anything, it must answer yes to one of these:

1. Does it make the trajectory computation more correct?
2. Does it make the result more usable by someone without mission-design
   training?
3. Does it make a claim more verifiable by a reader?

If none, it waits. "It will be cleaner in anticipation of future features" is
not a yes.

## Layer map

```
DATA        JPL Horizons, Small-Body Database
GEOMETRY    ephemerides, state vectors, frames, epochs
SOLVER      Lambert over hyperbolic targets, grid over departure/flight time
INTERPRET   Granite agent, groundedness gate
SURFACE     API, judges endpoints, web
```

Each layer consumes the one below it. The interpretation layer never reaches
past the solver to the data.

## Non-negotiables

**Every number is computed, never generated.** The model explains solver
output. It does not produce figures. A deterministic check compares every
numeric token in an explanation against the solver's output before the
explanation is returned, and that check is dispositive. Granite Guardian is
advisory on top of it.

**The solver runs before the agent, and completes.** The agent receives
structured output and cannot trigger a recomputation with different
parameters. This is what makes the groundedness check tractable: the set of
legitimate numbers is fixed before generation begins.

**Accessibility is a design gate, not a final phase.** No clone, no virtual
environment, no API key, works on a phone. A tool whose argument is that
existing software is inaccessible cannot itself be inaccessible. Any decision
that adds a setup step for the user needs a reason that survives this.

**Failures degrade the explanation, never the numbers.** If watsonx is down,
trajectories still compute and still render.

**Report disagreement.** Where HITS differs from published mission-design
figures, say so and by how much. A validation document that only reports
agreement is marketing.

**State the fidelity limits.** HITS models patched-conic transfers. It does
not do n-body integration and does not model non-gravitational forces. Say
this wherever a number is presented as authoritative.

## Discipline

**Validate with plots before believing numbers.** A porkchop grid that looks
wrong is wrong, and this has caught something real at every layer of every
project run this way.

**No solver behaviour is believed until a test or a plot demonstrates it.**
This includes reasoning that sounds correct, whether it came from a person or
an assistant. On a prior project an assistant reasoned its way to a bug that
did not exist, and only running the tests settled it. The hazard is worse
here, because a plausible wrong delta-v is far harder to spot than a plausible
wrong diagnosis. An explanation of what the code does is a hypothesis until
executed.

**Baseline the dependencies before building on them.** Record hapsira's and
astropy's own test and lint state before writing solver code, so pre-existing
breakage is never mistaken for something HITS introduced.

**Offline and credentialed results are reported separately.** Never let a
no-credentials floor be mis-credited to the credentialed system. Judges
endpoints state which path produced each figure.

**Write the validation once.** The same module is imported by the test suite
and by the judges endpoint, so proof in CI and proof in a browser cannot
drift apart.

**No aspirational entries.** If it is not built, it is not in the README, not
in the docs, and not in the demo. Roadmap items live in `specs/roadmap.md`
under Conditional and nowhere else.

**Small branches, conventional prefixes, one concern each.** Commit history is
read by judges.

**Record each tool session as it happens** in `docs/BOB_USAGE.md`, since it
cannot be reconstructed later. Bob drove Phase 1 and authored the Phase 2
adversarial corpus black-box; Claude Code authored the Phase 2 gate and the
agent layer above it. Which tool did what is a claim judges can check only if
it was written down at the time.

## Accuracy guardrails

Facts this project has already got wrong once, or is likely to. Correct them
here rather than rediscovering them. Anyone working in this repository, human
or assistant, should treat this list as authoritative over their own recall.

- **poliastro is archived.** It pulls astropy 3.x and fails to build on
  Python 3.12. The maintained fork is hapsira, same API. Do not write install
  instructions naming poliastro.
- **TRACE is The Aerospace Corporation's, not SwRI's.** SwRI's interstellar
  intercept software is separate and unnamed publicly. Both are internal. The
  Aerospace Corporation lineage traces to a 1964 orbit determination report,
  SSD-TDR-64-159.
- **The gap is usability, not availability.** GMAT and OITS are both free and
  public. Never write that no software exists, or that these tools are
  unavailable. The claim is that no *accessible* tool exists, and it is
  narrower and defensible.
- **Granite Speech is speech-to-text only.** Input, not output. There is no
  text-to-speech in the Granite family. A spoken reply would use the browser
  SpeechSynthesis API.
- **Granite is not required by the rules.** The rules require IBM Bob as the
  primary development tool and AI as a core functional component. Granite is
  listed as recommended. It is used here because judging scores effective use
  of IBM technologies, not because it is mandatory. Do not claim it is
  required.
- **"JPL-grade" is not a claim this project has earned.** HITS runs
  patched-conic Lambert solves, not GMAT-class modelling. The tagline is
  "Expert-level intercept analysis, open to everyone." If the phrase
  "JPL-grade" is ever used, a validation comparison against published figures
  must be shown alongside it.
- **The evidence corpus is 19,122 comments from six videos**, not five, and
  not a random sample of public interest. The figure was 14,293 until
  2026-08-30, when counting the committed files showed `trappist1.txt` holds
  5,902 comments rather than the 1,073 the table recorded. Re-running the
  extraction rule over the six files reproduces the 3,171 questions in
  `clusters.txt` exactly, which is what establishes that the larger corpus is
  the one that was clustered. Counts per file are in `docs/EVIDENCE.md` with
  the command that checks them, and the limits stated there should not be
  dropped when the number is quoted elsewhere.
- **The first clustering run failed and its output is not a result.** HDBSCAN
  directly on 384-dimensional embeddings collapsed to one cluster of 2,276
  questions. UMAP before clustering fixed it. Never cite the collapsed run.
- **The Granite model is `ibm/granite-4-h-small` on us-south, confirmed by a
  live call on 2026-08-30.** `ibm/granite-4-1-8b-instruct`, the earlier
  default, 404s on this account and was never servable here. Both are still
  overridden by `WATSONX_MODEL_ID` and `WATSONX_URL`.
- **An instruct model must be called through the chat endpoint.**
  `/ml/v1/text/generation` hands the prompt over raw, with no chat template,
  and Granite returned incoherent token spam on a prompt that reads perfectly
  well to a person. `agent/granite.py` uses `/ml/v1/text/chat` with a messages
  array so the template is applied server-side. Do not "simplify" it back.
- **The asserts in `ManifestEntry` have never run, and one of them guards the
  published-versus-computed seam.** `is_number` returns on its first line
  (`solver/manifest.py`, the property under `__post_init__`), so the four
  asserts written below the return are unreachable: that every entry's unit,
  frame and kind are inside their lexicons, that renderings are non-empty, and
  that a `kind="published"` entry carries its citation. They read as though
  they were meant to close `__post_init__`. The concern is not that they are
  dead, it is that nothing has ever checked what they check, so an entry may
  have been out of lexicon or uncited since Phase 2 and no test would have
  said so. The citation guard is the one that matters: attribution checking
  leans on published entries being distinguishable from computed ones, and an
  uncited published entry is exactly that seam failing quietly. **Verify the
  three frozen manifests and the validate manifest against all four
  conditions before handoff 2 wires Granite**, and only then decide whether
  the asserts move or become a test. A separate watched task, not a
  deadline-night edit. Found 2026-08-31 during the deploy handoff and
  deliberately not fixed there.

### Plan versus shipped

The single most likely failure mode in this repository is a document
describing something the code does not do. The specs were written before the
solver existed, so every claim in `docs/` is provisional until the
corresponding code lands.

When implementation diverges from a spec, correct the spec and record the
correction here. Do not let a planning document stand as a description of
shipped behaviour, and do not repeat a doc's claim externally without
checking the code first.

Phase 1 built and validated (initial 2025-07-13; revision completed 2026-08-27):
- solver/ package: constants, fetch, lambert, solve, grid, validate, plot
- tests/: test_baseline, test_fetch, test_lambert, test_solve, test_validation
- data/state_vectors.json: 6 committed entries (4 single states + 2 grid windows; 391 + 1044 states in grids)
- plots/c3_floor_slice.html: C3 porkchop slice, departure 2018-2032 vs duration 5-30 yr
- Validation result (revision): 41 passed, 1 skipped, 1 xfailed (matplotlib/NumPy2 pre-existing), 0 failed
- Frame gate: v_inf = 26.286 km/s vs 26.33 published (diff 0.044 km/s, PASS). Citation: Hein et al. 2019, p.553 col 1.
- C3 2027: 1331.16 km^2/s^2 vs 1400 published (diff 68.84, 4.92%, within 20% tol, PASS). Citation: p.554 col 1.
- C3 floor: 714.36 km^2/s^2 vs 703 published (diff 11.36, 1.62%, ASSERTED). Floor at 2018-06-04, TOF 30 yr. The extended-trend check on the committed oumuamua_c3_grid shows C3 dropping only 3.39 km^2/s^2 across the 30-to-44-yr span, so the curve has levelled and the duration-axis read is not mid-descent. Gap attributed to orbit-solution epoch drift (retrieval 2026-08-27 vs Lyra 2019). Citation: p.553 col 2 / Fig.1.
- Sample A: v_inf2 (eq.4) = 13.967 km/s vs 13.6 published (diff 0.367 km/s, within 2.0 tol, ASSERTED). v_arr_local = 13.716 km/s. Def. gap 0.251 km/s (hyperbolic geometry at 5.852 AU). Citation: p.554 col 2 / Fig.5.
- Sample B: v_inf2 (eq.4) = 0.642 km/s vs 0.6 published (diff 0.042 km/s, within 0.3 tol, ASSERTED). v_arr_local = 0.644 km/s. Encounter at 115.079 AU vs paper's 111.4 AU (3.7 AU orbit-solution drift). Citation: p.554 col 2 / Fig.6.
- All Lyra citations filled from Hein et al. 2019 (Acta Astronautica 161, 552-561). PDF committed to data/lyra/.
- Retrieval date for all state vectors: 2026-08-27.

Phase 2 built and validated (2026-08-29):
- solver/manifest.py: the manifest of every citable number for a call, 81
  entries for a full validate(). One canonical value per number, several
  declared renderings, generated by a pinned ladder so the gate never rounds.
  Contract in docs/MANIFEST.md.
- verify/extract.py and verify/exemptions.py: the three-clause rule telling a
  citable quantity from an incidental numeral, exemption table as data.
- verify/groundedness.py: membership (dispositive, plus unit and frame) and
  attribution (published versus computed). No arithmetic anywhere in the
  matching path, enforced by an AST test.
- verify/corpus.py and verify/corpus_ingest.py: Bob's black-box submission
  validated on its own schema, ingested into the canonical corpus.
- Corpus: 30 reject cases from Bob, 3 white-box reject cases, 14 accept cases,
  2 accepted limits, 3 quarantined with reasons.
- Suite: 156 passed, 1 skipped, 1 xfailed, 0 failed.
- Granite Guardian is not wired in; every verdict reports advisory unavailable.

Phase 2 agent layer built and validated (2026-08-29):
- agent/template.py: the deterministic floor. Two shapes, intercept
  feasibility from a solve manifest and the validation summary from a validate
  manifest. Takes the manifest and never the result object, so the floor sees
  exactly the universe the gate sees. Every number is a manifest rendering
  pulled by entry id; an AST test rejects any format specifier, rounding call,
  arithmetic operator, or numeric literal in the module.
- agent/explain.py: generate, gate, regenerate at most twice with the rejected
  tokens fed back, then serve the floor. One exit, and the floor is gated like
  any candidate. `served_by` is `granite_first_pass`, `granite_after_regen` or
  `deterministic_floor`, never collapsed.
- agent/granite.py: the watsonx client, the only place a credential is read,
  from the environment alone. Absent credentials are an ordinary outcome and
  give `deterministic_floor`. Never called by the test suite.
- The intercept template states no feasibility verdict. HITS computes what a
  transfer costs and does not model launch-vehicle capability, so it reports
  the cost and says the cost is the input to a judgement rather than the
  judgement.
- Suite: 191 passed, 1 skipped, 1 xfailed, 0 failed.
- Live run 2026-08-30, `ibm/granite-4-h-small` on us-south: the fixture
  validate manifest returned `granite_first_pass`, grounded, zero
  regenerations. The test suite still drives every path by stub, so what CI
  proves is the loop's behaviour and the live run is what proves the
  endpoint's.
- **Updated 2026-08-30, later the same day: it reproduces, on the solve shape,
  and what it returns is worse than the floor.** Eleven live calls on the
  intercept manifest gave seven `granite_after_regen` and four
  `deterministic_floor`. The regeneration works: attempt one is rejected for
  relabelling the eq. 4 quantity, the rejected token is fed back, attempt two
  passes. So do not repeat "the Granite path does not reproduce" as though it
  were still the whole story. What is still true, and is the sharper point, is
  that a grounded Granite answer is a flat one-figure-per-paragraph recital
  that drops the plain-language lead and the whole feasibility framing, and
  leaks `n_a`, an internal frame-lexicon placeholder, into user-facing prose.
  The README shows the floor, and says why: the floor is the path that
  reproduces byte-for-byte offline with no credentials. The `n_a` leak is a
  real defect and is not yet fixed.
- **Prompt restructure attempted 2026-08-30 and it made Granite worse. The
  recommendation is floor-first.** The `n_a` leak is fixed and stays fixed:
  `permitted_numbers()` omits the frame clause for a frameless entry, and a
  test asserts the placeholder is absent from the system turn, the user turn
  and a regeneration turn for all three objects. Moving the standing rules into
  the system turn and adding a plain-language-opening instruction was tried in
  the same change, and measured: **0 grounded out of 15** across the three
  objects. A controlled A/B with the rules back in the user turn and the `n_a`
  fix retained gave **4 grounded out of 5** on the same manifest, so the
  restructure caused the regression and the `n_a` fix did not.
- **The new failure mode is typography, not content.** Asked for prose a
  non-scientist can read, Granite writes like a journal: `km² s⁻²` and
  `km²/s²` for `km^2/s^2`, and U+2011 NON-BREAKING HYPHEN in `2018‑06‑07`,
  which stops the date matching its rendering and leaves `06` and `07` as
  loose numerals. The instruction to write plainly and the instruction to quote
  exactly pull against each other in this model. Do not treat this as a wording
  problem to iterate on; it was tried once, bounded, and the result is above.
- **Even when Granite passes, its prose is worse than the floor.** A grounded
  answer is a recital of one figure per paragraph with no plain-language lead
  and none of the feasibility framing, and it adds loose interpretive glosses
  the solver never made.
- **Gate upgrade measured 2026-08-30: three-object pass rate 0/15 to 10/15.**
  Typographic canonicalization, word forms for every unit, and a two-form
  closed set of date renderings. Measured live, five runs per object, on the
  same restructured prompt that had scored 0/15: 1I/'Oumuamua 5/5
  `granite_after_regen`, 3I/ATLAS 5/5 `granite_first_pass`, 2I/Borisov 0/5,
  rejected every time on a bare `13` from writing "March 13 2030" without its
  comma. Recognition of the comma-less shape was added after that measurement
  and its live effect is **unmeasured**, because the watsonx account hit
  `token_quota_reached` (HTTP 403) during the re-run. Do not quote a number for
  it. The 10/15 figure is the one that was watched.
- **A 403 quota failure serves the floor with `regens=0` and no findings.**
  That is the transport degrade path, not a gate rejection, and the two look
  similar in a summary table. Read `floor_reason` before concluding anything
  about grounding from a run of floors.
- **Still open, recorded rather than chased: an ordinal date spelling.**
  "the 7th of June, 2018" grounds, because `7th` carries a letter suffix and is
  not tokenized as a number, leaving only a grounded `2018`. It is the same
  fragmentation class as the closed limit below, in a shape the date patterns
  do not recognise.
- **That gate limit is now closed (2026-08-30).** A grounded 3I/ATLAS answer had
  contained "September 20, 2030", passing because `20` is `solve.tof_years` and
  `2030` is `solve.departure.year`. A date is now a single token: the tokenizer
  recognises date shapes and the phrase is looked up whole, so
  "March 20, 2030" is one fabricated token rather than two grounded digits.
  **Recognition is wider than acceptance and the two must not be conflated.**
  The manifest accepts two forms, ISO and "June 7, 2018". The tokenizer
  recognises more shapes than that on purpose, so an unaccepted spelling
  arrives as one unmatched phrase instead of fragmenting. Widening recognition
  only ever makes the gate stricter. A bare `Month YYYY` is deliberately not
  recognised, because "the June 2027 launch" is correct prose about a grounded
  year.
- **The earlier record, kept because it is what the runs showed then.** Later the same day, six live
  attempts across two manifest shapes were all rejected and all served
  `deterministic_floor`. On a solve manifest Granite rewrites `2017-06-07` as
  "June 7, 2017", so the gate rejects `7`; on the validate manifest it computes
  differences the manifest never emitted (0.11605, 0.04351, 7.252) and
  misattributes a published figure. Every attempt in a run came back
  byte-identical, so feeding the rejected tokens back changed nothing. Do not
  describe the Granite path as working: what is demonstrably working is the
  gate refusing it and the floor serving correct grounded prose. Runs recorded
  in `docs/BOB_USAGE.md`.
- The gate certifies grounding, not truth. The first live explanation carried
  only manifest renderings and still said the 2027 C3 comparison "exceeds the
  solver's tolerance of 20%" when 4.92% is inside 20%. Every number was
  grounded; the claim about them was false. Membership and attribution do not
  check a comparative assertion, and nothing in the manifest encodes a
  pass/fail verdict for the model to quote. Do not describe a grounded
  explanation as a correct one.

Three-object set built and validated (2026-08-30):
- data/fetch_objects.py: 2I/Borisov ("2I") and 3I/ATLAS ("3I") fetched down the
  same path 'Oumuamua uses, four pinned states committed. The six Lyra keys are
  untouched and the file diff is insertions only.
- The transfer for each is chosen by a stated rule, not taken from a source,
  because no published intercept study exists for either: the cheapest
  departure day of calendar year 2030 at a flight time of 7305 days, twenty
  years on the 365.25-day year and the duration class of Lyra's Sample B. Both
  C3 minima are interior to the year. Rule and scan recorded in
  docs/PROVENANCE.md.
- The frame check for these two is independent rather than published:
  state-derived ecliptic elements against the elements Horizons reports
  separately for the same body at the same epoch. Agreement to nine decimals
  on e, inclination and perihelion distance. Both hyperbolic, both outgoing.
- solver/objects.py: the fixed set of three, no free-text target anywhere.
  `verification_status` is a real field on the object, on the result, and in
  the serialized form, so a UI and a judges page render it per object. It is
  deliberately not a manifest entry: a claim about the literature is not a
  number the solver computed.
- solver/intercept.py: the render envelope. One manifest and one call_id per
  object, proven by a test that each object's answer fails the gate against
  both other manifests. Borisov and 3I/ATLAS share a flight time and a C3
  order of magnitude, so this is not theoretical.
- The deterministic floor answers all three and all three are grounded.
- **"Validated against published figures" attaches to 1I/'Oumuamua and to
  nothing else.** Borisov and 3I/ATLAS are computed with the same method and
  checked against no external figure, because none exists. Do not let the
  three-object count borrow 'Oumuamua's validation.
- The intercept template's framing was read back at 'Oumuamua's 393.34 and
  3I/ATLAS's 2919.78 km^2/s^2. The feasibility disclaimer carried over verbatim;
  the opening did not. "A transfer to the target exists" reads as a finding at
  the cheap end and as a misleading one at the expensive end, since a connecting
  trajectory exists between almost any pair of positions. The opening now says
  what that existence is worth and the closing limit states that the wording
  does not change with the size of the figure. **No threshold was added and none
  should be:** a line separating an affordable departure energy from an absurd
  one is a launcher model, and HITS has no launcher model. The template may say
  it is scale-blind; it may not say which side of a line a figure falls on.
- The intercept answer opens with a plain-language lead naming the target,
  the launch energy and the flight time, with the solver's vocabulary below it.
  The scale word is "a very high-energy departure", which is a statement about
  the class (an interstellar object is unbound and leaving, so chasing one is
  expensive whichever) and never a ranking. **A comparison against another
  object, or against any launcher, is forbidden here**: the first is a ratio
  the solver never emitted, the second is the launcher model this project does
  not have. The target's designation comes from the manifest header, not an
  entry, because a name is not a computed quantity.
- Suite: 208 passed, 1 skipped, 1 xfailed, 0 failed.

Currently unbuilt, and therefore not to be described as working: Granite
Guardian, every judges endpoint, the frontend, and the deployment.

## Provenance and reproducibility

- Ephemerides are cached and committed, so validation does not depend on
  Horizons being reachable
- Horizons data updates as observations accumulate; numbers carry the date
  they were computed
- Docker is the reproducibility boundary. A judge re-running validation gets
  identical numbers, not whatever their local astropy produces
- The evidence corpus, cluster report, and mining scripts stay in `/data`.
  Claims in the problem statement must resolve to files that exist

## Environment

- WSL2, `~/projects/hits`, Python 3.12.3 (`.venv/pyvenv.cfg` confirmed; stated 3.11 in error, corrected 2025-07-13)
- poliastro is archived and will not install on 3.12. hapsira is the
  drop-in replacement
- Design decisions in chat, mechanical implementation delegated
- Install-test the scientific stack on the host in week one

## Writing rules

- No em dashes. Use commas, colons, parentheses, or separate sentences
- Prose carries an argument forward in connected paragraphs. Bullets and bold
  labels are for material executed or verified line by line
- Stick to the data. If something is not in the source, leave it out and flag
  the gap rather than filling it in
