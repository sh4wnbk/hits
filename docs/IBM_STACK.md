# IBM Stack

Each IBM component, what it does, where it lives, and how to confirm it is
running. Components without a real job are not listed; the reasoning for what
was left out is in `specs/tech-stack.md`.

| Component | Role | Location | Verify |
|---|---|---|---|
| IBM Bob | Primary development tool | `BOB_USAGE.md` | Session records with dates and what changed |
| Granite (watsonx) | Reasoning layer: interprets solver output under the groundedness gate | `agent/explain.py`, `agent/granite.py` | `tests/test_explain_proof.py` drives every path with a stub; a served response carries `served_by` and, when Granite produced it, `model_id`. Live on 2026-08-30 against `ibm/granite-4-h-small` on us-south, logged in `BOB_USAGE.md` |

## Not wired

Listed because leaving them out of a document that judges read as an
inventory would let a plan be mistaken for a build.

**Granite Guardian.** Intended as an advisory second opinion on top of the
deterministic gate. No module exists. Earlier drafts of this document named
`agent/guardian.py`, which was never written. Every verdict the gate returns
reports its advisory field as `unavailable`, and the deterministic comparison
is what decides.

**Granite embeddings.** The committed evidence pipeline,
`data/cluster_questions.py`, embeds with `all-MiniLM-L6-v2`. A Granite
embedding re-run was planned and has not happened, so `data/clusters.txt` is a
MiniLM result and is the only cluster report in the repository.

## Why Granite

The rules require IBM Bob as the primary development tool and AI as a core
functional component. Granite is recommended rather than required. It is used
because judging scores effective use of IBM technologies, and because the
reasoning layer needs a model regardless of vendor.

## Boundary

Granite interprets. It does not compute. Every figure in a generated
explanation originates in the solver, and a deterministic check enforces this
before the explanation is returned. This boundary is the reason the system can
be trusted with a question where a plausible-sounding wrong number is worse
than no answer.

## Degrade

If watsonx is unavailable, or no credentials are present at all, the solver
still runs and the result renders with the deterministic template in
`agent/template.py`. That response reports `served_by: deterministic_floor`, so
a floor answer is never mis-credited to Granite. The IBM layer improves the
experience; it does not gate the answer.
