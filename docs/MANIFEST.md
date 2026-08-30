# Manifest Contract

The manifest is the single source of grounding. A generated explanation may
quote a number only if that number appears in the manifest for the solver call
being explained. The gate that enforces this is a membership test over strings
and nothing else: it never computes, and it is never permitted to re-derive a
number in order to justify it. If the gate could recompute 1.62% from 714.36
and 703, the guarantee would be that the gate can do arithmetic, not that the
explanation is grounded.

That constraint is what shapes everything below. Because the gate may not
round, the solver must enumerate in advance every string an explanation is
allowed to write for a given number. Because the gate may not divide, the
solver must emit the percentages, differences, and tolerances itself. The
manifest is therefore not a summary of the solver output. It is the complete,
closed set of quotable numbers, derived ones included.

## What emits a manifest

The manifest is emitted by the solver layer, from the public surface named in
CONVENTIONS.md and nothing deeper. The emitter reads `SolveResult`,
`GridResult`, `FrameGateResult`, `C3Result`, and `ArrivalResult`. It does not
import `solver.lambert`, does not touch raw frames, and does not re-read state
vectors. The interpretation layer, in turn, never reaches past the manifest to
the solver.

### What the no-arithmetic rule costs

Stating the guarantee without its price would be marketing. The gate cannot
distinguish a plausible rounding from an outright fabrication. Both reach it as
a string that no manifest entry renders, and separating them would mean
comparing magnitudes, which is the arithmetic the rule forbids. So both are
reported as `fabricated-number`, and a near-miss carries no gentler verdict
than an invention.

That is the right trade. A gate that could measure how close a wrong number is
would be a gate that computes, and the moment it computes, what it certifies is
its own arithmetic rather than the explanation's grounding. The attack's
character is not lost: the corpus records it in `attack_shape`, which is the
author's description of what they were attempting, kept separate from the
verdict the gate reached.

The same collapse takes two more codes with it, and for the same reason.

A number correctly derived from solver outputs that the manifest never emits,
such as the ratio of the computed C3 floor to the published one, reaches the
gate as a string absent from the index. So does an outright invention. Telling
them apart would mean performing the derivation, which is the arithmetic the
rule forbids, so `derived-not-emitted` is not a verdict either. It is worth
being explicit about what this means, because it sounds like a weakness and is
the opposite: a correctly derived figure is ungrounded, and the gate rejects it
exactly as firmly as a fabricated one. Arithmetic being right is not the same
as a number being one the solver produced.

A value from an earlier retrieval is the third. It was correct once, which is
precisely why it is dangerous, and it too arrives as a string this manifest
does not render. `stale-number` needs no verdict of its own: grounding against
one manifest, whose header carries its own `call_id` and retrieval date, is
already what makes a number from another run fail.

All three are covered by cases in `tests/corpus/adversarial_whitebox.jsonl`,
which prove the gate rejects them. What the corpus does not claim is that the
gate can say which kind of wrong they are.

## Structure

One manifest per solver call, serialized as JSON. A header, then a flat entry
list. Flat rather than nested, because the gate's only hot path is a lookup
from a rendering string to the entries that permit it, and nesting would buy
structure the gate cannot use.

### Header

| Field | Meaning |
|---|---|
| `manifest_version` | Contract version. Bumped when entry semantics change |
| `call_id` | UUID for this call. A number from a different call is ungrounded |
| `emitted_utc` | When the manifest was built |
| `producer` | `solve`, `grid`, or `validate` |
| `inputs` | State-vector keys used, their epochs, and their `retrieved_utc` |
| `fidelity_note` | Patched-conic, two-body, no n-body integration |
| `solver_git_sha` | Commit the numbers were produced at |

### Entry

| Field | Meaning |
|---|---|
| `id` | Stable dotted key, e.g. `validate.c3.floor.rel_diff_pct` |
| `label` | Human name for the reject report |
| `value` | Canonical float, rounded to `precision`. `null` only when `value_type` is `date` |
| `value_type` | `number` or `date`. Declared, never inferred from whether `value` is null |
| `text_value` | The content of a date entry. Empty for a number |
| `precision` | Decimals the solver computed to, declared per field |
| `unit` | From the closed unit lexicon below |
| `frame` | `earth_relative`, `target_relative`, `heliocentric`, `n_a` |
| `kind` | `computed`, `derived`, `published`, `tolerance`, `epoch`, `count`, `metadata` |
| `renderings` | Ordered list of permitted strings. First is canonical |
| `citation` | Required when `kind` is `published` |
| `provenance` | Which result field or fields the entry came from |

### Dates are text, not numbers

A calendar date has no float that means anything, so a date entry carries
`value: null` and holds its content in `text_value`. An earlier version filled
`value` with the year to satisfy the type, which made the entry look, in any
view that withholds renderings, like an ISO field that had silently lost its
month and day. It had not: the full date was always in `renderings` and always
groundable. But a field filled with a placeholder is a field that has stopped
meaning anything, and the next reader has no way to tell the placeholder from
the data.

The manifest therefore grounds a full calendar date and its year separately, as
two entries with different units. `2018-06-04` grounds as a date; `2018` grounds
as a `calendar_year`, which is what lets the unit check reject `2018 km^2/s^2`.

`value_type` is declared per entry and checked both ways at construction: a
number must have a value and no text, a date must have text and no value, and a
date must render as itself and nothing else. Nothing downstream is allowed to
key on `value is None` to decide what it is looking at. That distinction is
narrow and it matters: a check written that way stops separating "this is a
date" from "this number went missing", and the second is precisely what the
completeness test exists to catch. The set of entries permitted to be
non-numeric is pinned in `tests/test_manifest.py` as `DATE_TYPED_IDS`, so a new
one is added deliberately rather than appearing.

### Unit lexicon

Closed. `km/s`, `km^2/s^2`, `km`, `AU`, `d`, `yr`, `JD`, `%`, `deg`,
`calendar_year`, `1` (dimensionless). A unit outside this list is a contract
change, not a local choice.

Synonyms accepted from an explanation and normalized to the lexicon form:
`km^2/s^2` also matches `km²/s²` and `km2/s2`; `km/s` also matches
`kilometres per second` and `kilometers per second`; `%` also matches
`percent`; `d` also matches `day` and `days`; `yr` also matches `year` and
`years`; `AU` also matches `au`.

## Precision: one canonical value, several declared renderings

The manifest emits **one canonical value per number and several permitted
renderings of it**. This is a decision with a cost, so the reasoning is
recorded rather than assumed.

A single canonical rendering forces one of two failures. Either the gate
rejects "the floor is 714 km^2/s^2" as ungrounded when the manifest holds
`714.36`, which makes correct prose fail, or the gate rounds the candidate
before comparing, which is arithmetic and voids the guarantee. Enumerating the
permitted strings at emit time moves the rounding to the only layer allowed to
round, and leaves the gate with a hash lookup.

### The ladder

For an entry with canonical value `v` and declared `precision` `p`:

1. `v` is `round(raw, p)`. No rendering may ever exceed `p` decimals, so no
   rendering can claim more precision than the solver computed.
2. The ladder starts at the decimals `v` actually needs, trailing zeros
   stripped, capped at `p`. This is what prevents a value computed to five
   decimals but landing on `0.044` from emitting `0.04400`.
3. Rungs descend by one decimal to zero decimals.
4. A rung is kept if it carries three or more significant digits, or exactly
   two significant digits together with a fractional part. The canonical
   rendering is always kept regardless of this rule.
5. A rung ending in a trailing zero after the decimal point is dropped. It is
   never natural prose, and dropping it removes any ambiguity with the
   `precision-inflation` reject code.
6. A physical quantity whose canonical value is integral also renders with one
   decimal. "15 years" and "15.0 years" are equally correct prose, and
   rejecting the second would be a false positive on writing that is not wrong
   about anything. Counts, Julian Dates, and calendar years are excluded:
   nobody writes "391.0 states" or "2027.0".

Entries of kind `published` and kind `tolerance` emit exactly one rendering.
HITS does not get to re-round a figure it did not compute: Lyra's 26.33 is
quotable as `26.33` and not as `26.3`, and a declared tolerance of 0.5 km/s is
quotable as `0.5`. This also removes what would otherwise be a collision
between the computed frame-gate value and the published one at three
significant figures.

### The four pinned ladders

These are the contract, and `tests/test_manifest.py` regenerates them exactly.
If it cannot, the policy is not pinned and the emitter is wrong.

| Entry | Canonical | `precision` | Renderings |
|---|---|---|---|
| `validate.c3.floor.computed` | 714.36 | 2 | `714.36`, `714.4`, `714` |
| `validate.c3.floor.rel_diff_pct` | 1.62 | 2 | `1.62`, `1.6` |
| `validate.frame_gate.computed` | 26.28614 | 5 | `26.28614`, `26.2861`, `26.286`, `26.29`, `26.3` |
| `validate.arrival_b.v_inf2` | 0.64166 | 5 | `0.64166`, `0.6417`, `0.642`, `0.64` |
| `validate.frame_gate.abs_diff` | 0.04386 | 5 | `0.04386`, `0.0439`, `0.044` |
| `validate.arrival_b.definitional_gap` | 0.00186 | 5 | `0.00186`, `0.0019` |

The last two pin the sub-0.1 regime, where the two-significant-digits clause is
least obviously right. It needs no special case: leading zeros are not
significant, so the floor scales with magnitude on its own. `0.044` is two
significant figures with a fraction and survives; `0.04` is one and does not.
That matters because "the frame gate agrees to within 0.044 km/s" is the truest
sentence in the whole validation, and a gate that rejected it would be worse
than useless.

Three of the others are worth reading closely. The frame-gate ladder stops before a
bare `26`, which has two significant digits and no fractional part, so the
coarse rung that would let an explanation say "26 km/s" for a 26.28614 km/s
result is excluded. The Sample B ladder stops before `0.6`, which has one
significant digit, so HITS's computed 0.64166 km/s cannot be quoted as Lyra's
published 0.6 km/s: the two are separate entries with separate kinds, and the
explanation must say which it means. And the floor ladder reaches `714`, which
is how PROVENANCE.md and CLAUDE.md already quote it, while `710` appears on no
ladder at all.

### Collisions

Two entries may legitimately produce the same rendering. Collisions are
permitted, and a token matching several entries is grounded if any matched
entry satisfies both the unit and the frame constraint, with the reject report
naming all candidates. `Manifest.collisions()` lists them, and
`tests/test_manifest.py` holds a reviewed inventory: every collision carries a
written reason, and a new one fails the build until someone has looked at it.
Collisions accumulating unnoticed is how a gate quietly stops discriminating.

Most are entries that are simply equal: samples A and B share one launch
instant, both C3 tolerances are 20 percent, the floor's 30-year duration is
also the grid's longest. One is separated by unit and matters: `20` is both a
20 percent tolerance and a 20-year flight time.

One is a stated limit rather than a coincidence. Sample B's eq.4 asymptotic
velocity (0.64166 km/s) and its local encounter velocity (0.64351 km/s) both
reach `0.64` at the ladder's coarse end, in the same unit and the same frame,
so the gate cannot tell which quantity a bare "0.64 km/s" refers to. It does
not need to, because the sentence is true of both, and PROVENANCE.md already
records that the two nearly coincide at Sample B's distance. What the gate
cannot do is distinguish the labels, and that limit is recorded here rather
than discovered later.

## Completeness

Completeness is enforced mechanically, not by care. A test reflects over
`dataclasses.fields()` of all five public result types and asserts that every
float field has a manifest entry. A number cannot be dropped by an oversight,
only by editing the test, which shows up in review.

Derived entries that are not dataclass fields are enumerated in an explicit
declared list, and the same test asserts the list is fully emitted:

- Flight time in years alongside days
- Departure and arrival epochs as ISO date and as year-only, alongside the JD
- Tolerances as a percentage alongside the fraction
- Grid extents: departure count, duration count, axis bounds, window years
- The Lyra publication year and the retrieval year
- Encounter distance in AU
- Lyra's own stated flight times and encounter distances for both samples

The last of those is worth its own note. The paper gives Sample A as a 1.0-year
flight to 5.8 AU and Sample B as a 20.0-year flight to 111.4 AU. HITS computes
365 days, which is 0.99932 Julian years, and places the encounters at 5.852 AU
and 115.079 AU. The published figures are therefore emitted as their own
`published` entries rather than being treated as the same numbers, so an
explanation can state the disagreement and have both halves of it grounded.
Eliding the difference would be the more comfortable choice and the wrong one.

### Years are entries, not exemptions

Every four-digit year in an explanation is a citable quantity. There is no
exemption for calendar years, and the manifest carries every year an
explanation is entitled to say: the epoch entries emit year-only renderings,
and the header's `inputs` and `solver.lyra` supply the retrieval year and the
publication year.

The consequence is the point. "The 2027 launch" grounds against the 2027
departure epoch of the C3 read. "A 2018 departure" grounds against the floor's
departure. "Arrives in 2050", against a real 2037 arrival, matches nothing and
is rejected. The disguise this might otherwise open, a fabricated quantity
wearing a year's clothes, is closed by the unit check: `2018 km^2/s^2` matches
an entry whose unit is `calendar_year`, and a unit mismatch is a rejection even
though the digits matched.

## The printed rows are bound to the manifest

`print_frame_gate`, `print_c3_result`, and `print_arrival_result` print
canonical renderings pulled from the manifest rather than carrying their own
format specifiers. The binding is enforced by a dogfood test that runs the gate
over the solver's own printed validation output: if a printed row contains a
token the manifest does not carry, the build goes red. The manifest and the
validation rows a judge reads therefore cannot drift apart, and the derived
entries above cannot be quietly omitted, because the printed rows already
quote them.

## Scope

One manifest grounds one call. A real number from a different solve is
ungrounded, which is deliberate: `call_id` is what stops an explanation
borrowing a plausible figure from a neighbouring run.

Evidence-corpus figures, such as the 19,122 comments in `docs/EVIDENCE.md`, are
not solver output and appear in no solve manifest. If an explanation surface
ever needs to quote them they require their own manifest with its own
provenance. That is not built and is not in scope here.

## Fidelity

Every manifest carries the fidelity note in its header. HITS models
patched-conic transfers. It does not perform n-body integration and does not
model non-gravitational forces. A manifest entry is a faithful record of what
the solver computed, which is not the same as a claim that the number is
right to the precision it is quoted at.
