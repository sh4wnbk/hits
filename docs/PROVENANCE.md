# Provenance

The headline validation is offline and deterministic. It does not call Horizons
at run time; it reads state vectors committed to the repo. This document records
what those committed vectors are, when they were retrieved, and which published
Lyra figures each computed quantity is checked against. A judge re-running the
suite gets identical numbers because the inputs are frozen here.

Live Horizons is used only by the interactive /solve path, never by the
validation the submission's claim rests on.

## Committed state vectors

Each committed vector is a full six-component heliocentric state at a fixed
epoch. The fetch step writes these; the values below are TO BE FILLED by that
step and must not be hand-entered. Every row carries the date it was pulled,
because Horizons updates as observations accumulate and a number computed later
for the same target can differ.

Required vectors:

- Earth full state at each launch epoch (one per validation sample)
- 1I/'Oumuamua full state at each arrival epoch (one per validation sample)

| Body | Role | Epoch (TDB JD) | Frame | Center | Retrieved | State (km, km/s) |
|---|---|---|---|---|---|---|
| Earth | Sample A launch | GAP: epoch unpinned | ECLIPJ2000 | Sun | TO FILL | TO FILL |
| 1I/'Oumuamua | Sample A arrival | GAP: epoch unpinned | ECLIPJ2000 | Sun | TO FILL | TO FILL |
| Earth | Sample B launch | GAP: epoch unpinned | ECLIPJ2000 | Sun | TO FILL | TO FILL |
| 1I/'Oumuamua | Sample B arrival | GAP: epoch unpinned | ECLIPJ2000 | Sun | TO FILL | TO FILL |
| Earth | C3 slice launch (2027) | GAP: exact epoch to confirm | ECLIPJ2000 | Sun | TO FILL | TO FILL |
| 1I/'Oumuamua | self-check epoch | GAP: epoch to confirm | ECLIPJ2000 | Sun | TO FILL | TO FILL |

Frame, center, and time scale are fixed by CONVENTIONS.md and are not per-row
choices. The horizons id for the target is 1I/'Oumuamua (record the exact
Horizons designation string used, since it disambiguates the orbit solution).

## Blocker: sample A and B epochs

Samples A and B are the headline. Their arrival relative velocities are
published (below), but the exact launch and arrival epochs are known only as
"2017 launch, ~1 year flight" (A) and "2017 launch, ~20 year flight" (B). The
committed vectors cannot be fetched until these are pinned to instants.

Resolution: extract the epochs from the Lyra source during this step. If the
source gives a launch date and a flight duration rather than two instants,
record both and derive the arrival epoch, and note the derivation here. If the
source is ambiguous, the two samples are reported *with the epoch ambiguity
stated in the result*, not silently resolved to a convenient value.

Where the launch day stays unresolved, the fallback is a launch-day sweep at
the published flight time: hold the flight duration at Lyra's value, step the
launch day across the plausible window, and report the arrival relative
velocity as a range against the published scalar, stating whether the published
value falls inside that range. Do not select the launch epoch by minimizing
departure C3. Minimum-C3 selection belongs to the C3 floor quantity, where the
cheapest launch is the thing being compared; applied to the arrival-velocity
samples it substitutes a different transfer for Lyra's and the comparison stops
being a reproduction. The swept window defines exactly which Earth and target
states are fetched and committed, so the samples stay offline.

## Published Lyra constants

The five quantities the solver is checked against. Values are as carried in the
project's decided validation design. The citation column is TO BE FILLED from
the Lyra source (page, table, or figure) before this doc is committed. A value
without a citation is not usable as a validation target.

| # | Quantity | Value | Units | Frame | Lyra citation |
|---|---|---|---|---|---|
| 1 | Target heliocentric v_inf (self-check) | 26.33 | km/s | heliocentric | GAP: page/table |
| 2 | Departure C3, 2027 launch | 1400 | km^2/s^2 | Earth-relative | GAP: page/table |
| 3 | Departure C3 floor | 703 | km^2/s^2 | Earth-relative | GAP: page/table |
| 4 | Arrival relative velocity, sample A | 13.6 | km/s | target-relative | GAP: page/table |
| 5 | Arrival relative velocity, sample B | ~600 | m/s | target-relative | GAP: page/table |

Context to record alongside each citation when filled: the launch epoch and
flight time the figure corresponds to, the transfer type (direct vs Oberth-
assisted), and whether the figure is a single scalar or read off a plot.

Sample B's value is a small difference of two large heliocentric velocities and
carries a wide, explicitly stated tolerance. It is a near-rendezvous stress
case, not a co-equal headline with sample A. The tolerance figure is set in the
validation module, not here.

## Explicitly excluded, not comparison targets

Recorded so they are never later mistaken for validation targets:

- **Oberth / JOM total delta-v** (Table 1 total ~18.3 km/s; JOM ~15.8 km/s).
  These are total mission delta-v with a solar or Jupiter Oberth maneuver and
  are not reproducible by a patched-conic Lambert solve. Not a target.
- **Lyra's 33 to 76 km/s heliocentric range.** This is a heliocentric figure
  and is not a target for the Earth-relative departure C3. Different frame.

## Retrieval discipline

Every committed number carries its retrieval date. The C3 floor comparison
reports the gap between the measured interior minimum and Lyra's 703 as orbit-
solution drift tied to the retrieval date. The gap is reported, never tuned
away by adjusting flight time.