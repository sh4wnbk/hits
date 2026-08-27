# IBM Stack

Each IBM component, what it does, where it lives, and how to confirm it is
running. Components without a real job are not listed; the reasoning for what
was left out is in `specs/tech-stack.md`.

| Component | Role | Location | Verify |
|---|---|---|---|
| IBM Bob | Primary development tool | `docs/BOB_USAGE.md` | Session records with dates and what changed |
| Granite (watsonx) | Reasoning layer: calls the solver as a tool, interprets output | `agent/` | `/explain` returns a generated explanation with `model` field populated |
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

If watsonx is unavailable, the solver still runs and results still render with
a templated explanation. The IBM layer improves the experience; it does not
gate the answer.
