# Candidate chip questions, mined from the corpus

A selection menu, not a design. Nothing here is built, no answer is defined,
and `explain()` was not called. Shawn picks; the build is a later handoff.

Every candidate below is real mined text from the committed corpus. Where a
chip label differs from the mined phrasing, both are given, because the
rewriting is where a question can quietly turn into a claim HITS does not make.

## Provenance

The corpus is the six committed comment files. Re-running the extraction rule
in `data/cluster_questions.py` (a line containing `?`, at least four words,
leading enumeration stripped) over them reproduces **3,171 questions exactly**,
which is the figure `data/clusters.txt` records, so the text quoted here is the
text that was clustered.

```
curiosity_animation.txt     1215
trappist1.txt               1084
7min_terror.txt              378
oumuamua.txt                 316
3iatlas_known.txt             91
3iatlas_mars.txt              87
TOTAL                       3171
```

Cluster ids are from `data/clusters.txt`; the six themes are declared in
`data/plot_demand.py:57-65`.

## The constraint that shaped this list

**Only 494 of the 3,171 questions, 15.6 percent, come from the three
interstellar-object files.** The corpus is mostly Mars rovers and TRAPPIST-1.
This matters for chip selection in a way worth stating before the candidates:
the largest and most fluent question clusters in the corpus are about objects
HITS does not compute for, and a chip drawn from them would be a question the
tool cannot answer no matter how well it is phrased.

The travel-time theme is the clearest case. Clusters 45, 10, 48 and 49 are
large and on their face perfect, but read closely they are asking how far away
the TRAPPIST-1 planets are in light years and how long a crewed trip would
take. HITS answers neither. Only the question *shape* transfers; the subject
has to be an interstellar object for the answer to exist.

## What HITS can answer with a gated number

An object manifest holds twelve entries, and this is the whole universe a chip
answer may quote:

```
solve.c3            departure characteristic energy      km^2/s^2
solve.dv_depart     hyperbolic excess speed at departure km/s
solve.v_arr         relative speed at encounter          km/s
solve.v_inf2        asymptotic arrival relative velocity km/s
solve.tof_days      flight time                          d
solve.tof_years     flight time                          yr
solve.departure.iso / .year / .jd   departure epoch
solve.arrival.iso / .year / .jd     arrival epoch
```

Four question shapes are covered: how long the flight takes, what the departure
costs, how fast the probe meets the object, and when it would leave and arrive.

**One near miss worth naming.** Cluster 37 asks what the object's own speed is
("So , what is it's speed ? Is the trajectory hyperbolic ?", "At what a speed is
it traveling"). HITS does not emit that. `solve.v_arr` and `solve.v_inf2` are
the *probe's* speed relative to the target at encounter, which is a different
quantity, and a chip that asked the mined question and answered with those
numbers would be answering a question it was not asked. It is excluded for that
reason and not because the cluster is small.

---

# Bucket 1: OBJECT chips

Answered with a gated number from the object's own manifest. Each candidate
names the entry ids that answer it, so the selection rule is checkable rather
than asserted.

### O1. Flight time
- **Mined** (c45, size 69): "how long will it take us to get there?"
- **Mined** (c45): "now the real question: how long would it take to get there?"
- **Chip label**: "How long would the flight take?"
- **Answered by**: `solve.tof_days`, `solve.tof_years`
- **Note**: cluster 45 is a TRAPPIST-1 cluster. The phrasing transfers to an
  interstellar object cleanly; the subject does not, so the label must be read
  against the selected object and never against "there".

### O2. Departure energy
- **Mined** (c42, size 23, oumuamua): "It's such a shame that there's no
  practical way to get a probe to it."
- **Mined** (3iatlas_known): "Does NASA whish to send a probe to sample
  3I/ATLAS lef behind dust?"
- **Chip label**: "What would it cost to launch?"
- **Answered by**: `solve.c3`, `solve.dv_depart`
- **Note**: "cost" here is launch energy, not money. If that reads as budget to
  a general reader, the alternative label is "How much launch energy would it
  take?", which is longer and unambiguous.

### O3. Encounter speed
- **Mined** (c42, oumuamua): "Surely we are going to want to send a probe to
  sample materials?"
- **Mined** (oumuamua): "Do we even have anything that could intercept that?,
  even if we knew it was coming like 10 years ago? I guess we could have put
  something in its path to get a few fly-by pics, but it looks to fast to..."
- **Chip label**: "How fast would the probe pass it?"
- **Answered by**: `solve.v_arr`, `solve.v_inf2`
- **Note**: the second mined question is the closest thing in the corpus to the
  actual encounter-speed question, and it arrives already carrying the intuition
  that speed is the problem. It is also, in its own words, asking whether an
  intercept is possible; see the warning below.

### O4. Launch and arrival dates
- **Mined** (c42, trappist1): "Are we going to go send a probe there? If so,
  when is the right time to do so?"
- **Chip label**: "When would it have to launch?"
- **Answered by**: `solve.departure.iso`, `solve.arrival.iso`
- **Note**: HITS reports the departure epoch of a committed transfer. It does
  not search for the best launch date at request time, so "the right time" is
  answerable only as "the date this committed transfer departs". If that gap
  matters, the label should be "When does this transfer launch and arrive?"

## Excluded from the object bucket, with reasons

These are the strongest mined questions that did not qualify. They are listed
so the exclusions are reviewable rather than invisible.

| Mined question | Cluster | Why excluded |
|---|---|---|
| "Can we intercept it with a probe?" | c42, oumuamua | Asks for a feasibility verdict. See the warning below. |
| "why did we not catch it like a big fish???" | c42, oumuamua | Feasibility verdict, and presupposes a failure HITS does not assess. |
| "Wow scientists you could not catch it!? ... you could have send a vehicle to pick it up" | oumuamua | Sample return, not a flyby transfer. Nothing in the manifest answers it. |
| "So , what is it's speed ? Is the trajectory hyperbolic ?" | c37 | The object's own speed. Not a manifest entry; see the near miss above. |
| "How far away is it?" | c10, c48, c49 | Distance to TRAPPIST-1. HITS emits no distance entry at all. |
| "so it's a confirmed comet?" | c13 | Classification. HITS does not classify. |
| "Is it possible to build such a spacecraft?" (paraphrase of several) | c42 | Launcher capability. HITS has no launcher model. |
| Funding, life, religion clusters | c58, c51, c18 | Not mission-design questions. Largest clusters in the corpus, excluded on the rule. |

## Warning: the best-phrased question in the corpus is one HITS refuses to answer

"Can we intercept it with a probe?" is, by a clear margin, the most on-point
question anyone in this corpus asked. It is also a feasibility verdict, and
CLAUDE.md is explicit that HITS computes what a transfer costs and does not
model launcher capability, so the intercept template deliberately states no
verdict and the wording does not change with the size of the figure.

This is a decision for Shawn rather than something to resolve silently. Three
options, and I would take the second:

1. **Drop it.** Honest, and loses the question the corpus most wants asked.
2. **Recast the label to the cost question** and let the answer's existing
   framing do the work: the chip reads "What would it cost to catch it?", the
   answer gives the departure energy and says plainly that the cost is the
   input to a feasibility judgement rather than the judgement. The mined
   question is quoted as provenance, not used as the label.
3. **Use the mined phrasing as the label** and rely on the answer to decline.
   This is the one to avoid: a chip that asks "can we" and returns a number
   reads as a yes.

---

# Bucket 2: EVIDENCE chips

About the tool's own credibility and the gap it fills. These map to committed
evidence Shawn will define, not to gated numbers, and that difference should
stay visible in whatever the chips finally look like.

### E1. Why has nobody done this
- **Mined** (3iatlas_known): "Why isn't there spacecraft waiting to intercept
  any interstellar objects for scientific purposes?"
- **Mined** (oumuamua): "Why didn't you guys capture it? How many more
  decades/centuries/ EONS are you going to have to wait until another one comes
  by?"
- **Chip label**: "Why hasn't anyone gone after one?"
- **Answers from**: the Project Lyra study (`data/lyra/`), and the accuracy
  guardrail that the gap is usability rather than availability. **The answer
  must not say no software exists.** GMAT and OITS are both free and public.

### E2. Has anyone actually tried
- **Mined** (oumuamua): "Surely we are going to want to send a probe to sample
  materials? I so want there to be a message inscribed on the surface :)
  Clarke's Rama definitely springs to mind"
- **Chip label**: "Has anyone studied this seriously?"
- **Answers from**: Hein et al. 2019, committed at
  `data/lyra/hein_2019_acta_161_552.pdf`. Yes, and HITS is validated against
  five of its published figures.

### E3. How do we know the numbers are right
- **Mined** (oumuamua): "Do you have proof that this is an interstellar object?
  No? ok..."
- **Mined** (3iatlas_mars): "3rd object ever? How do we know?"
- **Chip label**: "How do we know these numbers are right?"
- **Answers from**: the frame gate and the four Lyra comparisons, and
  `verification_status` per object. **This chip carries the honesty
  constraint that matters most.** The validation attaches to 1I/'Oumuamua and
  to nothing else; Borisov and 3I/ATLAS are computed the same way and checked
  against no published figure, because none exists. An evidence chip that let
  the three-object count borrow 'Oumuamua's validation would be the single
  worst thing on the page.

### E4. Are the numbers invented
- **Mined** (oumuamua): "You have no proof of that ? Show the evidence ...all you
  have observations ..."
- **Mined** (oumuamua): "How do you know? Theory?"
- **Chip label**: "Could the AI be making these numbers up?"
- **Answers from**: the live gate demo, already deployed at
  `/gate/demo/{key}`. It shows the check accepting the solver's figure and
  rejecting a one-digit alteration of it, with the reason code, and no model
  involved.

## A caution on the evidence bucket

The credibility-flavoured questions in this corpus are heavily conspiracy
adjacent. The same searches that surfaced E1 and E4 also returned "Answer: NASA
lies", "Are we being lied too?", and a flat-earth post. Those are real mined
text and they are not chip candidates: answering them on their own terms would
put HITS in the position of rebutting a conspiracy rather than showing its
work.

The four above were selected because each has a committed artefact behind it (a
PDF, a validation comparison, a `verification_status` field, a live endpoint).
A credibility chip with no artefact behind it is a reassurance, and this project
does not ship reassurances.

## What is not decided here

The answer text for any chip, whether evidence answers are gated the way
numeric ones are, how many chips appear, and where they sit. All of that is the
build handoff.
