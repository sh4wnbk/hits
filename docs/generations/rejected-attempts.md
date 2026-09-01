# Rejected attempts, transcribed from run output

The four `.json` files beside this one are byte-exact copies of what
`data/generate_answer.py` wrote. The texts below never became files. They are
attempts the gate refused, printed to the terminal by the script and copied
here verbatim from that output.

The distinction matters and is why they are in a separate file. A `.json` here
is the artefact. A block below is a transcription of one, faithful to the run
but not a copy of a file, because no file existed.

Some attempts are gone entirely. The first floored borisov run of the evening,
three attempts, predates the change that made the script print rejected prose,
so only its tokens survive, in `BOB_USAGE.md`. That absence is the reason
the change was made.

Model for every run below: `ibm/granite-4-h-small`, us-south.

---

## 2I/Borisov, 01:14:30Z, attempt 0

Rejected on `[('March 13 2030', 'fabricated-number'), ('March 13 2050',
'fabricated-number'), ('1', 'fabricated-number'), ('728', 'fabricated-number')]`.
A comma-less date, twice, and `1 728` written with a space as the thousands
separator. Attempt 1 grounded and became
`2026-08-31-borisov-could-intercept.json`.

> The solver's output shows that a spacecraft could intercept the interstellar object 2I/Borisov in a patched-conic, two-body trajectory with no n-body integration or non-gravitational forces. The mission would depart Earth on March 13 2030, with a departure C₃ of 1 728 km² s⁻² (the "departure C₃") and would give the spacecraft a hyperbolic excess speed of about 41.57 km s⁻¹ relative to Earth. Once it reaches the comet's vicinity, the spacecraft would be moving at roughly 16.89 km s⁻¹ relative to 2I/Borisov, which is the local encounter speed. The flight time works out to about 7305 days, or roughly 20 years, between launch and arrival. All of these numbers come from a patched‑conic, two‑body calculation that does not include any n‑body effects or non‑gravitational forces.

---

## 2I/Borisov, 01:28:22Z, attempt 0

The first live catch by the `unsourced-attribution` rule, made minutes after
the rule was written. Rejected on `[('reported in the source paper',
'unsourced-attribution')]`. Attempt 1 dropped the clause and grounded.

> The solver's output shows that a spacecraft could intercept the interstellar object 2I/Borisov in a patched-conic, two-body trajectory with no n-body integration or non-gravitational forces. The mission would depart Earth on March 13, 2030, with a departure C3 of 1727.89 km²/s² and a hyperbolic excess speed of 41.56787 km/s relative to Earth. The flight time to reach 2I/Borisov would be 7305 days, or approximately 20 years, arriving on March 13, 2050. At arrival, the spacecraft would have a relative velocity of 16.89188 km/s with respect to the object, which is close to the asymptotic value of 16.93682 km/s reported in the source paper.

## 2I/Borisov, 01:28:22Z, the grounded answer

`granite_after_regen`, grounded, one regeneration. It was written to
`data/answers/borisov.json` and overwritten four minutes later when the floor
was frozen in its place, so no file survives. It is the cleanest Granite answer
of the evening and it still claims the mission could be flown.

> The solver's output shows that a spacecraft could intercept the interstellar object 2I/Borisov in a patched-conic, two-body trajectory with no n-body integration or non-gravitational forces. The mission would depart Earth on March 13, 2030, with a departure C3 of 1727.89 km²/s² and a hyperbolic excess speed of 41.56787 km/s relative to Earth. The flight time to reach 2I/Borisov would be 7305 days, or approximately 20 years, arriving on March 13, 2050. At arrival, the spacecraft would have a relative velocity of 16.89188 km/s with respect to the object.

---

## 3I/ATLAS, three attempts, all rejected

The run floored. No file was written, by design. All three attempts were
rejected on a spelled-out `twenty`, and the sequence is worth reading as a
sequence: the model repaired the first instance every round and never the one
in the closing sentence, which is the rejected token being fed back and
partially applied.

Every attempt also opens with a feasibility claim, so this run would have
failed review even had it grounded.

**Attempt 0**, rejected on `[('twenty', 'spelled-out-quantity'), ('twenty',
'spelled-out-quantity')]`:

> The solver shows that a spacecraft could fly from Earth to the interstellar object 3I/ATLAS in about twenty years, leaving Earth on September 20, 2030, and arriving at the target on September 20, 2050. The departure from Earth would require a C₃ of 2919.78 km²/s², which is the energy needed to escape Earth's gravity into a hyperbolic trajectory. Once the craft leaves Earth, it would travel at about 54.035 km/s relative to Earth, and when it reaches 3I/ATLAS it would be moving at about 14.288 km/s relative to the object. The total time in flight would be 7305 days, or roughly twenty years.

**Attempt 1**, rejected on `[('twenty', 'spelled-out-quantity')]`. The first
`twenty` became `20.0 years`; the last sentence is unchanged:

> The solver shows that a spacecraft could fly from Earth to the interstellar object 3I/ATLAS in about 20.0 years, leaving Earth on September 20, 2030, and arriving at the target on September 20, 2050. The departure from Earth would require a C₃ of 2919.78 km²/s², which is the energy needed to escape Earth's gravity into a hyperbolic trajectory. Once the craft leaves Earth, it would travel at about 54.035 km/s relative to Earth, and when it reaches 3I/ATLAS it would be moving at about 14.288 km/s relative to the object. The total time in flight would be 7305.0 days, or roughly twenty years.

**Attempt 2**, rejected on `[('twenty', 'spelled-out-quantity')]`. The opening
became `20 years`; the last sentence is unchanged again:

> The solver shows that a spacecraft could fly from Earth to the interstellar object 3I/ATLAS in about 20 years, leaving Earth on September 20, 2030, and arriving at the target on September 20, 2050. The departure from Earth would require a C₃ of 2919.78 km²/s², which is the energy needed to escape Earth's gravity into a hyperbolic trajectory. Once the craft leaves Earth, it would travel at about 54.035 km/s relative to Earth, and when it reaches 3I/ATLAS it would be moving at about 14.288 km/s relative to the object. The total time in flight would be 7305.0 days, or roughly twenty years.
