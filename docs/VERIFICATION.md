# Verification

HITS states that its numbers are correct. This is how that is demonstrated
rather than asserted.

## Every claim with the step that settles it

Each row pairs a claim with the minimal command or check that decides it. A
claim without a verification step is not a claim, it is a hope.

| Claim | Verification step |
|---|---|
| Solver reproduces published intercept figures | `pytest tests/test_validation.py::test_lyra_oumuamua -v` — prints computed vs published delta-v and the difference |
| Energy is conserved along computed arcs | `pytest tests/test_physics.py::test_energy_conservation` |
| Hyperbolic excess velocity matches target eccentricity | `pytest tests/test_physics.py::test_vinf_consistency` |
| Lambert solutions satisfy their boundary conditions | `pytest tests/test_physics.py::test_lambert_boundary` |
| Explanations contain no number the solver did not produce | `pytest tests/test_groundedness.py` — includes a deliberately ungrounded fixture that must be rejected |
| Validation runs without credentials | CI job `validate` runs with no secrets configured; a leaked credential requirement turns it red |
| Numbers still render when watsonx is down | `pytest tests/test_degrade.py::test_explain_without_watsonx` |
| Cached ephemerides match Horizons | `python -m verify.ephemeris_drift` — reports difference and cache date |
| Docs describe only shipped behaviour | CI job `docs-honesty` compares CLAUDE.md's unbuilt list against the module tree |
| Deployed URL is reachable | keepalive workflow pings `/health` every ten minutes and fails loudly |

## What is verified

**Solver accuracy.** Intercept solutions are checked against published
mission-design literature, principally Project Lyra's 'Oumuamua studies, which
report delta-v requirements and flight times for specific mission
architectures. HITS reproduces those scenarios and reports the difference.

Agreement is reported as a number with a stated tolerance, not as a claim of
correctness. Where HITS disagrees, the disagreement is reported.

**Physical sanity.** Independent of any published comparison:

- Energy and angular momentum conservation along computed arcs
- Hyperbolic excess velocity consistent with the target's orbital eccentricity
- Lambert solutions satisfying the boundary conditions they were solved for
- Departure delta-v magnitudes bounded below by the physically minimum
  transfer

**Groundedness.** Every numeric token in a generated explanation must appear
in the solver output that produced it. Deterministic set comparison,
dispositive. Granite Guardian runs as an advisory second layer; its verdict is
reported but does not override the deterministic check.

## What is not verified

Stated plainly, because a verification document that omits its limits is
marketing.

- HITS models patched-conic transfers. It does not perform full n-body
  integration, and results will diverge from high-fidelity tools for long
  arcs or close planetary encounters.
- Solar radiation pressure and non-gravitational forces are not modelled.
  Interstellar objects have exhibited non-gravitational acceleration, so
  ephemeris uncertainty for a given target may exceed solver error.
- No launch-vehicle model. Delta-v is reported as a requirement, not matched
  against a specific rocket's capability.
- Horizons ephemerides update as observations accumulate. Numbers computed
  today may differ from numbers computed later for the same target, which is a
  property of the data rather than an error.

See `docs/UNCERTAINTY.md` for magnitudes.

## Reproducing it

The validation suite runs offline with no credentials, because the solver
requires none. Cached ephemerides are committed so the run does not depend on
Horizons being reachable.

```
docker build -t hits .
docker run hits pytest tests/test_validation.py -v
```

The same code is exposed at `/validation`, so a judge can see the result
without cloning anything. Both paths run the identical module.

## Credentialed versus offline

Results state which path produced them, in separate fields, so an offline
floor is never mis-credited to the credentialed system.

| Layer | Credentials | Verifiable in CI |
|---|---|---|
| Solver validation | None | Yes |
| Physical sanity checks | None | Yes |
| Groundedness (deterministic) | None | Yes |
| Groundedness (Guardian) | watsonx | No — reported from last successful run |
| Explanation quality | watsonx | No |

CI gates on everything in the credential-free rows. The remainder is reported
with its timestamp.
