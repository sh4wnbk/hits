# Conventions Contract

The single set of frame, center, time, and unit choices every layer obeys.
Confusing any two of these produces numbers that look plausible and are wrong,
which is the exact failure mode HITS exists to avoid. This contract is
authoritative over any looser wording elsewhere. Bob does not deviate from it
without a recorded decision.

## Frame

All state vectors and all computation are in heliocentric ecliptic J2000
(ECLIPJ2000). Position in km, velocity in km/s. There is no second working
frame. The one Earth-relative quantity, departure C3, is computed from
heliocentric states and labeled Earth-relative at every point it appears; it
does not introduce a geocentric working frame.

## Center and source

State vectors come from JPL Horizons with center = Sun (@sun) and reference
plane = ecliptic (ECLIPJ2000). Horizons returns vectors in AU and AU/day; HITS
converts to km and km/s once, at the fetch boundary, and everything downstream
is km and km/s. The conversion happens in exactly one place.

The fetch uses astroquery Horizons with center = Sun and refplane = 'ecliptic'.
Confirming the frame requires an orientation-dependent quantity, not the speed
magnitude: speed is identical in ecliptic and equatorial J2000, so a
heliocentric-speed check catches a wrong center but not a wrong plane. Confirm
the plane by checking an inclination or an out-of-plane component against the
published orbit, and confirm the center by the heliocentric speed. Record both.

## Time

Epochs are TDB Julian Dates. Epochs passed to Horizons are TDB. UTC and TT are
not used for propagation or solving anywhere. An epoch is an instant, not a
calendar date (see GLOSSARY.md).

## Units

- Distance: km
- Velocity: km/s
- C3 and v_inf-squared: km^2/s^2
- Gravitational parameter k: km^3/s^2
- Time of flight: seconds internally (the unit hapsira.iod.izzo.lambert
  consumes), reported to users in days

Reported figures state their units inline. No figure is presented bare.

## Gravitational parameter

k is the Sun's GM, taken from astropy.constants.GM_sun converted to km^3/s^2
(approximately 1.327e11 km^3/s^2), pinned once in a constants module and
imported everywhere. The same k is used by the fetch sanity checks, the solver,
and the validation. It is never redefined locally.

## Lambert branch selection

Transfers are direct: zero revolutions (M = 0), prograde. For M = 0 the
solution is determined by the prograde sense and the transfer geometry. Any
additional branch argument the call exposes, for example lowpath, is left at the
hapsira default and its effect confirmed by the boundary test, not set on
assumption. Retrograde or multi-revolution branches are used only if a specific
validation case requires one, and any such use is flagged in that case's result
and here.

Bob must confirm the installed hapsira 0.18.0 lambert signature and its default
arguments against this intent, by running one solve and checking the terminal
velocities satisfy the boundary conditions, before any validation number is
trusted. The intended branch is a hypothesis until that check runs.

## hapsira scope

Only hapsira.iod.izzo.lambert and hapsira.core.* are used. The Lambert call is
hapsira.iod.izzo.lambert(k, r0, r, tof), with k in km^3/s^2, positions in km,
and tof in seconds, returning departure and arrival velocities in km/s. This
signature and its unit expectations are confirmed by the boundary-condition test
before any validation number is trusted, not assumed. hapsira.twobody,
hapsira.ephem, and hapsira.plotting are broken on astropy 8 (matrix_product
removed) and on matplotlib under numpy 2, and are not imported. HITS owns its
own Horizons fetch, cache, and state handling. Plotting is plotly. The venv is
Python 3.12. The known-good full-API pin set (numpy 1.26.4 + astropy 6.1.7 +
hapsira 0.18.0) is an escape hatch only and is not the working environment.

## Public surface

The solver package exposes three functions and hides Lambert mechanics behind
them:

- `solve(target, departure_epoch, flight_time)` — one transfer; returns the
  arrival state and the derived departure C3 and arrival relative velocity
- `grid(target, departure_range, flight_range)` — the C3 and arrival-velocity
  surfaces over the grid
- `validate()` — the Lyra comparison, reading committed state vectors, printing
  the comparison rows

Nothing outside the package calls Lambert directly or touches raw frames. The
groundedness gate and the tests assert at this surface, not inside it.