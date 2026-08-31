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

| Body | Role | Epoch or window (TDB) | Frame | Center | Retrieved (UTC) | Committed states |
|---|---|---|---|---|---|---|
| 1I/'Oumuamua | self-check (perihelion) | single, 2017-09-09 00:00:00 (JD 2458005.5) | ECLIPJ2000 | Sun | 2026-08-27T18:36:35Z | 1 state (position/velocity at perihelion epoch) |
| Earth | Sample A/B launch | single, 2017-06-07 12:00:00 (JD 2457912.0) | ECLIPJ2000 | Sun | 2026-08-27T19:52:26Z | 1 state, shared by A and B |
| 1I/'Oumuamua | Sample A arrival | single, 2018-06-07 12:00:00 (JD 2458277.0) | ECLIPJ2000 | Sun | 2026-08-27T19:52:27Z | 1 state at 5.852 AU |
| 1I/'Oumuamua | Sample B arrival | single, 2037-06-07 12:00:00 (JD 2465217.0) | ECLIPJ2000 | Sun | 2026-08-27T19:52:29Z | 1 state at 115.079 AU |
| Earth | C3 grid launch window | window, 2018-01-01 to 2032-12-13, 14-day step | ECLIPJ2000 | Sun | 2026-08-27T19:52:50Z | 391 states (JD 2458119.5 to 2463579.5) |
| 1I/'Oumuamua | C3 grid arrival window | window, 2023-01-01 to 2062-12-24, 14-day step | ECLIPJ2000 | Sun | 2026-08-27T19:52:52Z | 1044 states (JD 2459945.5 to 2474547.5) |

The C3 grid window reproduces Fig. 1, whose launch-date axis runs from
01-Jan-2018 to the early 2030s and whose duration axis runs 5 to 30 years. The
1400 km^2/s^2 point at a 2027 launch is read off this same grid at the 2027
launch column near 15-year duration; it needs no separately committed states.
The window rows expand to sets of 14-day-step state vectors in `state_vectors.json`
over their `[start, end]` ranges; the rows record the bounds and step count, the
JSON holds the states. Horizons id used for all 1I/'Oumuamua fetches is "1I".

Frame, center, and time scale are fixed by CONVENTIONS.md and are not per-row
choices. The Horizons id for the target is 1I/'Oumuamua (record the exact
Horizons designation string used, since it disambiguates the orbit solution).
The launch instant 2017-06-07 12:00:00 is committed in TDB as stated; the
roughly 69-second UTC-versus-TDB offset at that date is far below every sample
tolerance and is noted here rather than resolved.

## The two objects with nothing to validate against

2I/Borisov and 3I/ATLAS are computed down the same path as 1I/'Oumuamua and
are validated against nothing, because nobody has published an intercept study
for either. That is a difference in what is known, not a difference in method,
and it is recorded here and carried as a field on every result rather than
left to a reader to infer.

| Body | Role | Epoch (TDB) | Frame | Center | Retrieved (UTC) | Committed states |
|---|---|---|---|---|---|---|
| Earth | 2I/Borisov intercept departure | single, 2030-03-13 00:00:00 (JD 2462573.5) | ECLIPJ2000 | Sun | 2026-08-31T00:27:12Z | 1 state at 0.9938 AU |
| 2I/Borisov | 2I/Borisov intercept arrival | single, 2050-03-13 00:00:00 (JD 2469878.5) | ECLIPJ2000 | Sun | 2026-08-31T00:27:12Z | 1 state at 209.4517 AU |
| Earth | 3I/ATLAS intercept departure | single, 2030-09-20 00:00:00 (JD 2462764.5) | ECLIPJ2000 | Sun | 2026-08-31T00:27:13Z | 1 state at 1.0045 AU |
| 3I/ATLAS | 3I/ATLAS intercept arrival | single, 2050-09-20 00:00:00 (JD 2470069.5) | ECLIPJ2000 | Sun | 2026-08-31T00:27:13Z | 1 state at 305.7675 AU |

Horizons ids are "2I" and "3I", which resolve to `Borisov (C/2019 Q4)` and
`ATLAS (C/2025 N1)` respectively. Both were confirmed by a live call before the
states were committed.

### Why these epochs

The 'Oumuamua samples take their epochs from Hein et al. 2019, so the epoch
choice is not a choice at all: it is what reproducing a published figure
requires. Neither of these objects has a source to take epochs from, so the
transfer is chosen by a rule, and the rule is stated so that a reader can see
it is not a search for a flattering number:

> the cheapest departure day in calendar year 2030, at a flight time of 7305
> days.

2030 is after discovery for both objects and after the retrieval date, so the
departure is a departure rather than a hindcast. 7305 days is twenty years on
the 365.25-day year, which is the flight duration the paper uses for Sample B,
so both unvalidated transfers sit in the same duration class as the one
'Oumuamua transfer with a published arrival figure behind it. The day was found
by solving every departure day of 2030 at that flight time against the matching
arrival state and taking the minimum departure C3. Both minima are interior to
the year rather than on its edge, so neither is an artefact of where the scan
was cut. The scan is exploratory and is not committed; the four states the
chosen transfers read are.

### The frame check without a published figure

The 'Oumuamua frame check sets heliocentric speed and inclination against
published values. These objects have no published intercept study, and quoting
orbital elements from recall is the fabricated citation this repository exists
to refuse, so the check is made independent rather than published: the ecliptic
osculating elements derived from the committed state vector are compared
against the elements Horizons itself reports for the same body at the same
epoch, requested separately from the vectors. A state that came back in the
equatorial frame would disagree by up to 23.4 degrees of inclination, and a
barycentric rather than heliocentric center would move the eccentricity.

| Body | Quantity | From the committed state | Horizons elements | Difference |
|---|---|---|---|---|
| 2I/Borisov | eccentricity | 3.32195 | 3.32195 | 9.43e-10 |
| 2I/Borisov | inclination | 44.7746 deg | 44.7746 deg | 6.75e-13 |
| 2I/Borisov | perihelion distance | 1.97665 AU | 1.97665 AU | 1.83e-10 |
| 3I/ATLAS | eccentricity | 6.00201 | 6.00201 | 1.82e-09 |
| 3I/ATLAS | inclination | 175.1605 deg | 175.1605 deg | 5.68e-14 |
| 3I/ATLAS | perihelion distance | 1.32012 AU | 1.32012 AU | 6.81e-11 |

Both are hyperbolic and both are on the outgoing leg at the arrival epoch,
which the eq. 4 arrival computation requires and which `solver/solve.py` raises
on rather than assumes. The retrieval discipline below applies unchanged: these
numbers carry 2026-08-31 and a later retrieval for the same target can differ.

### What is not claimed

Nothing here is a validation. The states are frame-checked and the elements
agree with Horizons, which establishes that HITS is computing over the orbit
Horizons holds, and establishes nothing at all about whether the transfer
figures are right. `solver/objects.py` carries that distinction as the
`verification_status` field, and the string for these two objects says so in
the words a reader sees.

## Epoch blocker: resolved

The blocker is closed by the source. Fig. 5 (p.555) gives Sample A as launch
2017-06-07 12:00:00, ToF 1.0 year, encounter at 5.8 AU, arrival relative
velocity 13.6 km/s. Fig. 6 (p.556) gives Sample B as the same launch, ToF 20.0
years, encounter at 111.4 AU, arrival relative velocity 0.6 km/s. Both samples
therefore share one launch instant and have exact flight times, so each arrival
epoch is the launch plus the stated duration: Sample A arrives 2018-06-07
12:00:00, Sample B arrives 2037-06-07 12:00:00.

Sample B encounter distance: HITS places 1I at 115.079 AU (retrieved 2026-08-27)
vs Lyra Fig. 6 at 111.4 AU. The 3.7 AU gap is orbit-solution drift between
Lyra's 2019 ephemeris and the 2026 retrieval, not a solver discrepancy. The same
calendar date maps to a different position because Horizons refines the orbit
solution as new observations accumulate.

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

Extended-trend confirmation (Phase 1 closeout, 2026-08-27): the oumuamua_c3_grid
extends to 2062-12-24, giving ~44-yr TOF from a 2018-06-04 departure. C3 at
30 yr is 714.36 km^2/s^2; at 44 yr it is 710.97 km^2/s^2 — a drop of only
3.39 km^2/s^2 across the full 30-to-44-yr span. The curve has effectively
levelled. The C3 floor is therefore ASSERTED: 714.36 km^2/s^2 (HITS, 2026
retrieval) vs 703 km^2/s^2 (Lyra) = 1.6% agreement, attributed to orbit-solution
drift. Lyra's Fig. 1 also stops at 30 years and reads the same converged floor
region; neither value is a mid-descent boundary read.

## Perihelion self-check epoch

JD 2458005.5 (2017-09-09 00:00:00 TDB) is HITS's chosen self-check anchor for
the frame-gate validation. It is the single epoch retrieved near 1I/'Oumuamua's
perihelion passage and is used only as the heliocentric v_inf reference. It is
not a validation target requiring a published perihelion-passage date and carries
no external citation obligation.

## Retrieval discipline

Every committed number carries its retrieval date. Horizons ephemerides update
as observations accumulate, so a number computed later for the same target can
differ. Comparisons report the gap against the published Lyra figure with the
retrieval date attached, as drift, not as error to be tuned out.