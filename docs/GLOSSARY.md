# Glossary

Ubiquitous language for HITS. Referenced from CLAUDE.md. Every term here has an
everyday-sounding cousin that produces output which reads fine while being
wrong. When a doc, a test name, or a Bob prompt uses one of these words, it
means the definition below and nothing looser.

## Physical quantities

**delta-v**: The magnitude of a propulsive velocity change a spacecraft must
produce, counted as a scalar propellant-cost budget. Trap: "velocity change"
used loosely to mean the vector difference between the spacecraft's velocity
and the target's. That difference is arrival relative velocity, not a delta-v,
unless the spacecraft actually burns to cancel it.

**hyperbolic excess velocity (v_inf)**: The speed of a body relative to a
central body at infinite distance on a hyperbolic orbit, the residual speed
left after climbing out of the gravity well. Trap: escape velocity is the speed
needed to just barely reach infinity with zero residual; v_inf is the speed
above that. Related to C3 by C3 = v_inf squared. Computed from any state on the
orbit as v_inf = sqrt(v^2 - v_esc^2) = sqrt(v^2 - 2*mu/r), the square root of a
difference of squares, not the difference of the speeds v and v_esc.

**C3 (characteristic energy)**: Twice the specific orbital energy of a
departure hyperbola, units km^2/s^2, numerically v_inf squared. In HITS,
departure C3 is always Earth-relative: the energy a launch vehicle must impart.
Trap: do not compare an Earth-relative C3 against a heliocentric v_inf figure.
They are different frames (see Frames).

**arrival relative velocity**: The magnitude of the vector difference between
the spacecraft's velocity and the target's velocity at the arrival epoch, in
the heliocentric frame. This is the flyby speed. A rendezvous requires burning
it off; an intercept does not.

**escape velocity**: The speed at a given radius that reaches infinity with
exactly zero residual speed. Listed only to keep it distinct from v_inf.

## Frames and time

**frame**: The reference axes and origin a vector is expressed in. HITS uses
one frame for all computation: heliocentric ecliptic J2000 (ECLIPJ2000). A
state vector without its frame is meaningless.

**heliocentric / geocentric / barycentric**: Centered on the Sun, the Earth, or
the solar-system barycenter respectively. HITS state vectors and transfers are
heliocentric. Departure C3 is the one Earth-relative quantity and is labeled as
such wherever it appears.

**epoch**: A precise instant tied to a time scale (a TDB Julian Date in HITS),
at which a state vector is valid. Trap: "date" is a calendar day and is
ambiguous without a time and a scale. Every committed state vector carries its
epoch.

**TDB / TT / UTC**: TDB (Barycentric Dynamical Time) is the dynamical scale
solar-system ephemerides are expressed in and the only scale HITS propagates
in. UTC carries leap seconds and is wrong for propagation. Do not mix them.

## Solver terms

**state vector**: Position and velocity together (six components) at an epoch in
a frame. Trap: position alone (three components) cannot solve a transfer or
propagate. When a doc says "state," it means all six.

**Lambert problem**: Given two position vectors and a time of flight, find the
connecting conic arc and its two terminal velocity vectors. The solver core.

**patched-conic**: Modeling a trajectory as a sequence of two-body conic arcs
patched at boundaries, ignoring simultaneous multi-body gravity and
non-gravitational forces. This is HITS's fidelity ceiling and is stated
wherever a number is presented as authoritative.

**prograde / retrograde**: Direction of orbital motion relative to the
reference plane. A Lambert branch selector. HITS solves prograde, zero-
revolution transfers unless a validation case forces otherwise (see
CONVENTIONS.md).

**ephemeris / ephemerides**: Tabulated states of a body over time. HITS pulls
these from JPL Horizons and commits the ones the headline validation depends
on.

**porkchop grid**: A contour surface of a transfer cost (C3 or arrival relative
velocity) over departure epoch against flight time. Reveals launch windows.
HITS grids and plots slices of this surface; it does not tune flight time to
hit a target number.

## Mission types

**intercept (flyby)**: Arrive at the target's position at the arrival epoch
with nonzero relative velocity and fly past. Cheap.

**rendezvous**: Arrive at the target's position and match its velocity
(relative velocity near zero). Costs a large arrival burn. Trap: intercept and
rendezvous are different missions with very different delta-v. HITS sample A is
an intercept; sample B is a near-rendezvous stress case. Never let the two
share a sentence without the distinction stated.

## HITS-specific

**groundedness**: The property that every numeric token in a generated
explanation also appears in the solver output that produced it. Enforced by a
deterministic set comparison that is dispositive, with Granite Guardian
advisory on top.

**Project Lyra**: The Initiative for Interstellar Studies' published studies of
missions to 1I/'Oumuamua, and the source HITS validates its numbers against.
Specific figures and their citations are in PROVENANCE.md.

**self-check (frame gate)**: The heliocentric v_inf reproduction of the
target's own orbit (~26.33 km/s for 1I), run first and pass/fail, before any
mission-cost comparison. Kept uncoupled from the C3 floor.