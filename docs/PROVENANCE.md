# Provenance

The headline validation is offline and deterministic. It does not call Horizons
at run time; it reads state vectors committed to the repo. This document records
what those committed vectors are, when they were retrieved, and which published
Lyra figures each computed quantity is checked against. A judge re-running the
suite gets identical numbers because the inputs are frozen here.

Live Horizons is used only by the interactive /solve path, never by the
validation the submission's claim rests on.

## Source

All five validation constants come from one paper:

Hein, A. M., Perakis, N., Eubanks, T. M., Hibberd, A., Crowl, A., Hayward, K.,
Kennedy, R. G. III, Osborne, R. (2019). "Project Lyra: Sending a spacecraft to
1I/'Oumuamua (former A/2017 U1), the interstellar asteroid." Acta Astronautica
161, 552 to 561. DOI 10.1016/j.actaastro.2018.12.042.

The committed PDF is `data/lyra/hein_2019_acta_161_552.pdf`. Page and figure
references below are to this paper.

## Committed state vectors

Each committed entry is one or more full six-component heliocentric states at
fixed epochs. Sample entries are single-epoch: the source pins the launch to an
instant and both flight times to the year, so there is no sweep and no window
for the samples. Only the C3 grid is windowed, because reproducing the C3 floor
requires scanning launch date against mission duration. The fetch step writes
these; the values below are TO BE FILLED by that step and must not be
hand-entered. Every entry carries the date it was pulled, because Horizons
updates as observations accumulate and a number computed later for the same
target can differ.

| Body | Role | Epoch or window (TDB) | Frame | Center | Retrieved | Committed states |
|---|---|---|---|---|---|---|
| 1I/'Oumuamua | self-check (perihelion) | single, ~2017-09-09 (confirm at fetch) | ECLIPJ2000 | Sun | TO FILL | 1 state, TO FILL |
| Earth | Sample A/B launch | single, 2017-06-07 12:00:00 | ECLIPJ2000 | Sun | TO FILL | 1 state (shared by A and B), TO FILL |
| 1I/'Oumuamua | Sample A arrival | single, 2018-06-07 12:00:00 | ECLIPJ2000 | Sun | TO FILL | 1 state, TO FILL |
| 1I/'Oumuamua | Sample B arrival | single, 2037-06-07 12:00:00 | ECLIPJ2000 | Sun | TO FILL | 1 state, TO FILL |
| Earth | C3 grid launch window | window, 2018-01-01 to 2032-12-13, daily | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |
| 1I/'Oumuamua | C3 grid arrival window | window, launch + (5 to 30 yr), to ~2062 | ECLIPJ2000 | Sun | TO FILL | daily set, TO FILL |

The C3 grid window reproduces Fig. 1, whose launch-date axis runs from
01-Jan-2018 to the early 2030s and whose duration axis runs 5 to 30 years. The
1400 km^2/s^2 point at a 2027 launch is read off this same grid at the 2027
launch column near 15-year duration; it needs no separately committed states.
The window row expands to a set of daily state vectors in `state_vectors.json`
over its `[start, end]` range; the row records the bounds and step, the JSON
holds the states.

Frame, center, and time scale are fixed by CONVENTIONS.md and are not per-row
choices. The Horizons id for the target is 1I/'Oumuamua (record the exact
Horizons designation string used, since it disambiguates the orbit solution).
The launch instant 2017-06-07 12:00:00 is committed in TDB as stated; the
roughly 69-second UTC-versus-TDB offset at that date is far below every sample
tolerance and is noted here rather than resolved.

## Epoch blocker: resolved

The blocker is closed by the source. Fig. 5 (p.555) gives Sample A as launch
2017-06-07 12:00:00, ToF 1.0 year, encounter at 5.8 AU, arrival relative
velocity 13.6 km/s. Fig. 6 (p.556) gives Sample B as the same launch, ToF 20.0
years, encounter at 111.4 AU, arrival relative velocity 0.6 km/s. Both samples
therefore share one launch instant and have exact flight times, so each arrival
epoch is the launch plus the stated duration: Sample A arrives 2018-06-07
12:00:00, Sample B arrives 2037-06-07 12:00:00.

Both samples are single pinned transfers and both are asserted. The launch-day
sweep, the window-width reporting, and the assert-versus-report branch were
fallbacks for a source that did not pin the epochs. The source pins them, so
that machinery is retired for the samples and is not used.

Sample B keeps a wide, explicitly stated tolerance even though it is asserted.
At its 111.4 AU encounter the Sun still contributes on the order of 0.3 km/s to
each body's speed above its asymptotic value, which is a large fraction of the
0.6 km/s target, so B remains a sensitive near-rendezvous stress case. The
tolerance figure is set in the validation module, not here.

## Definitional note: which arrival velocity

The paper's arrival relative velocity v_inf,2 is defined by its equation 4 as
the difference of the two heliocentric hyperbolic-excess (asymptotic, at-infinity)
velocities of the spacecraft and the target. HITS's solver natively computes the
local encounter relative velocity, the vector-difference magnitude of the two
velocities at the arrival point. At Sample B's 111.4 AU these nearly coincide; at
Sample A's 5.8 AU they differ by several km/s, because 'Oumuamua's local speed
there is about 31.6 km/s against its 26.33 km/s asymptotic value. To reproduce
13.6 and 0.6 faithfully, compute the equation-4 asymptotic difference for the
head-to-head comparison and separately report the local encounter relative
velocity as HITS's native flyby number. Label both. If they differ, report the
gap as a definitional difference, not as error to be tuned toward the published
value.

## Published Lyra constants

The five quantities the solver is checked against, with page, column, and figure
references to the committed paper.

| # | Quantity | Value | Units | Frame | Lyra citation |
|---|---|---|---|---|---|
| 1 | Target heliocentric v_inf (self-check) | 26.33 | km/s | heliocentric | p.552 abstract/intro, restated p.553 col 1 |
| 2 | Departure C3 floor | 703 | km^2/s^2 | Earth-departure | p.553 col 2; Fig. 1 (colorbar floor 707 at earliest launch) |
| 3 | Departure C3, 2027 launch | 1400 | km^2/s^2 | Earth-departure | p.554 col 1 (37.4 km/s, ~15-year duration) |
| 4 | Arrival relative velocity, sample A | 13.6 | km/s | target-relative | p.554 col 2; Fig. 5 (launch 2017-06-07, ToF 1.0 yr, 5.8 AU) |
| 5 | Arrival relative velocity, sample B | 0.6 | km/s | target-relative | p.554 col 2; Fig. 6 (launch 2017-06-07, ToF 20.0 yr, 111.4 AU) |

The C3 floor sits at the earliest launch and longest duration in Fig. 1. Its
Earth-departure v_inf is 26.5 km/s, which is numerically close to the target's
26.33 km/s heliocentric v_inf but is a different quantity in a different frame.
Keep them in separate tables so they are never conflated.

## Explicitly excluded, not comparison targets

Recorded so they are never later mistaken for validation targets:

- Jupiter-gravity-assist plus Solar Oberth total delta-v, 18,332 m/s (Table 1,
  p.557). This is a total mission delta-v with a Jupiter flyby and a Solar Oberth
  maneuver and is not reproducible by a patched-conic Lambert solve. Not a target.
- The 33 to 76 km/s range (p.554, restated p.555) is an Earth-departure
  hyperbolic excess velocity for mission durations of 30 to 5 years at launches in
  2022 to 2027. It is the same Earth-relative family as the 1400 km^2/s^2 figure
  (37.4 km/s sits inside it), not a separate heliocentric quantity. It is not used
  as a validation target, but it is not excluded on a frame basis, and it must not
  be labeled heliocentric.

## C3 floor: reproduction note

The 703 km^2/s^2 floor lives at a 2017 to 2018 launch. Fig. 1 shows C3 climbing
steeply as the launch date moves later, and the 1400 km^2/s^2 figure is that
same curve at a 2027 launch. A departure grid that starts later than 2018 cannot
reach the floor. The C3 grid must scan launch over 2018 to 2032 against duration
5 to 30 years to reproduce Fig. 1 whole, which requires 'Oumuamua arrival states
out to roughly 2062. The floor sitting on the early-launch edge is physical, not
a truncation artifact, because 2017 to 2018 is the earliest meaningful launch;
the boundary-minimum suspect flag applies to the duration axis, not to that edge.
The gap between the measured floor and 703 is reported as orbit-solution drift
tied to the retrieval date, never tuned away by adjusting flight time.

## Retrieval discipline

Every committed number carries its retrieval date. Horizons ephemerides update
as observations accumulate, so a number computed later for the same target can
differ. Comparisons report the gap against the published Lyra figure with the
retrieval date attached, as drift, not as error to be tuned out.