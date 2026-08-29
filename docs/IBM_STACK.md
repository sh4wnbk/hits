# IBM Stack

Each IBM component, what it does, where it lives, and how to confirm it is
running. Components without a real job are not listed; the reasoning for what
was left out is in `specs/tech-stack.md`.

| Component | Role | Location | Verify |
|---|---|---|---|
| IBM Bob | Primary development tool | `docs/BOB_USAGE.md` | Session records with dates and what changed |
| Granite (watsonx) | Reasoning layer: interprets solver output under the groundedness gate | `agent/explain.py`, `agent/granite.py` | `tests/test_explain_proof.py` drives every path with a stub; a served response carries `served_by` and, when Granite produced it, `model_id`. No live call has been made yet |
| Granite Guardian | Advisory groundedness check on explanations | `agent/guardian.py` | `/faithfulness` reports the advisory verdict alongside the deterministic one |
| Granite embeddings | Sentence embeddings in the evidence pipeline | `data/cluster_questions.py` | `/evidence` reports which embedding model produced the cluster report |

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
