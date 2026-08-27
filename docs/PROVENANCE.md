# Provenance

The headline validation is offline and deterministic. It does not call Horizons
at run time; it reads state vectors committed to the repo. This document records
what those committed vectors are, when they were retrieved, and which published
Lyra figures each computed quantity is checked against. A judge re-running the
suite gets identical numbers because the inputs are frozen here.

Live Horizons is used only by the interactive /solve path, never by the
validation the submission's claim rests on.

## Committed state vectors

Each committed entry is one or more full six-component heliocentric states at
fixed epochs. Single-epoch entries commit one state; window entries commit a set
of daily states over a stated range, because the sample A and B sweeps and the
2027 C3 slice each consume a window, not a point. The fetch step writes these;
the values below are TO BE FILLED by that step and must not be hand-entered.
Every entry carries the date it was pulled, because Horizons updates as
observations accumulate and a number computed later for the same target can
differ.

| Body | Role | Epoch or window (TDB) | Frame | Center | Retrieved | Committed states |
|---|---|---|---|---|---|---|
| 1I/'Oumuamua | self-check (perihelion) | single, GAP: confirm epoch | ECLIPJ2000 | Sun | TO FILL | 1 state, TO FILL |
| Earth | C3 slice launch window (2027) | window, daily, GAP: confirm bounds | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |
| Earth | Sample A launch window | window, daily, GAP: bounds from source precision | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |
| 1I/'Oumuamua | Sample A arrival window | window, daily, GAP: A launch window + A flight duration | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |
| Earth | Sample B launch window | window, daily, GAP: bounds from source precision | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |
| 1I/'Oumuamua | Sample B arrival window | window, daily, GAP: B launch window + B flight duration | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |

Each window row expands to a set of daily state vectors in `state_vectors.json`
over its `[start, end]` range at the stated step. The row records the window
bounds and step; the JSON holds the states. Frame, center, and time scale are
fixed by CONVENTIONS.md and are not per-row choices. The Horizons id for the
target is 1I/'Oumuamua (record the exact Horizons designation string used, since
it disambiguates the orbit solution). The width of each sample window is set by
source precision (see Blocker) and is recorded here once resolved.

## Blocker: sample A and B epochs

Samples A and B are the headline. Their arrival relative velocities are
published (below), but the exact launch and arrival epochs are known only as
"2017 launch, ~1 year flight" (A) and "2017 launch, ~20 year flight" (B), with
arrivals near 2018 and 2037 respectively (2037 is the approximate arrival year,
not a launch year). The committed vectors cannot be fetched until the launch
windows are pinned.

Ordering: the Lyra source read is the first action of Sub-task 2, before any
state is fetched. That read pins each sample's launch window and flight duration
and fills the citation fields below. The swept-window state vectors and the
citations are both derived from it, so it precedes the fetch, not follows it.

Resolution: extract the epochs from the Lyra source. If the source gives a
launch date and a flight duration rather than two instants, record both and
derive the arrival epoch, and note the derivation here. If the source is
ambiguous, the affected sample is reported *with the epoch ambiguity stated in
the result*, not silently resolved to a convenient value.

Where the launch day stays unresolved, the fallback is a launch-day sweep at the
published flight time: hold the flight duration at Lyra's value, step the launch
day across the window, and report the arrival relative velocity as a range
against the published scalar, stating whether the published value falls inside
that range. Do not select the launch epoch by minimizing departure C3.
Minimum-C3 selection belongs to the C3 floor quantity, where the cheapest launch
is the thing being compared; applied to the arrival-velocity samples it
substitutes a different transfer for Lyra's and the comparison stops being a
reproduction. The swept-window states are committed in Sub-task 2, so the
samples stay offline.

The sweep window must be as narrow as the source precision allows, and its width
is reported in the result. A wide window that contains the published value is a
weak result, because a months-wide sweep of a fast-receding target contains
almost any plausible arrival velocity, so containment there is close to
automatic and proves little. The output states the window width so the strength
of the result is legible rather than implied.

Assert versus report follows source precision, and is decided at the Sub-task 2
read, not fixed in advance:

- If a sample's launch is pinned to a narrow window (a day, or a span tight
  enough that the swept range is not near-trivially wide), that sample is
  asserted against its published scalar.
- If a sample is known only to year and flight duration, that sample is reported
  with its range and window width, not asserted. This applies to sample A on the
  same footing as sample B. Sample A is not asserted by default; it is asserted
  only if the source pins it.

Sample B is expected to be reported-only. Its value is a small difference of two
large heliocentric velocities and carries a wide, explicitly stated tolerance.
It is a near-rendezvous stress case, not a co-equal headline with sample A.

## Published Lyra constants

The five quantities the solver is checked against. Values are as carried in the
project's decided validation design. The citation column is TO BE FILLED from
the Lyra source (page, table, or figure) during the Sub-task 2 read, before any
of these is used as a target. A value without a citation is not usable as a
validation target.

| # | Quantity | Value | Units | Frame | Lyra citation |
|---|---|---|---|---|---|
| 1 | Target heliocentric v_inf (self-check) | 26.33 | km/s | heliocentric | GAP: page/table |
| 2 | Departure C3, 2027 launch | 1400 | km^2/s^2 | Earth-relative | GAP: page/table |
| 3 | Departure C3 floor | 703 | km^2/s^2 | Earth-relative | GAP: page/table |
| 4 | Arrival relative velocity, sample A | 13.6 | km/s | target-relative | GAP: page/table |
| 5 | Arrival relative velocity, sample B | ~600 | m/s | target-relative | GAP: page/table |

Context to record alongside each citation when filled: the launch epoch and
flight time the figure corresponds to, the transfer type (direct vs Oberth-
assisted), whether the figure is a single scalar or read off a plot, and for
samples A and B whether the source pins the launch (assert) or gives only year
and duration (report).

## Explicitly excluded, not comparison targets

Recorded so they are never later mistaken for validation targets:

- **Oberth / JOM total delta-v** (Table 1 total ~18.3 km/s; JOM ~15.8 km/s).
  These are total mission delta-v with a solar or Jupiter Oberth maneuver and
  are not reproducible by a patched-conic Lambert solve. Not a target.
- **Lyra's 33 to 76 km/s heliocentric range.** This is a heliocentric figure and
  is not a target for the Earth-relative departure C3. Different frame.

## Retrieval discipline

Every committed number carries its retrieval date. The C3 floor comparison
reports the gap between the measured interior minimum and Lyra's 703 as orbit-
solution drift tied to the retrieval date. The gap is reported, never tuned away
by adjusting flight time.