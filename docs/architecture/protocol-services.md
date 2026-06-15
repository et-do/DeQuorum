# Protocol services

The protocol surface an integrator calls — the stable contract that turns "any LLM"
into attributed, governed, paid knowledge. These are in-process facades today
(nothing is deployed), each a thin wrapper over a protocol-core package, decoupled
from `web`/HTTP and from internal store wiring. The point of the seam: lifting one
into its own deployable service (the [services-roadmap](services-roadmap.md)'s
`ledger` carve-out) is wrapping the facade in transport, not a rewrite.

Both live in `dequorum.services`.

## `LedgerService` — payout / attribution audit boundary

Owns settlement and the payout journal, and nothing else — the clean money-path
boundary the services-roadmap wants split out before public launch.

```python
from dequorum.services import LedgerService

ledger = LedgerService(chat_store, contribution_store)

# settle an answer (equal split by default; inject faithful weights to override)
ledger.settle(message_id, revenue=1.0)
ledger.settle(message_id, revenue=1.0, credit_weights={cid: 0.75, other: 0.25})

# settle with the faithful, quality-grounded marginal (§8.6) — off the hot path
ledger.settle_faithful(message_id, revenue=1.0, model=model, embedder=embedder)

# read the audit boundary
ledger.get(message_id)        # the payout for one answer, or None
ledger.journal(session_id)    # the session's payout journal, oldest-first
```

| Method | Contract |
| --- | --- |
| `settle(message_id, revenue, *, split=None, credit_weights=None)` | Settle + persist; idempotent per message. `credit_weights` is the faithful-credit slot; omit for equal split. Returns `Settlement`. |
| `settle_faithful(message_id, revenue, *, model, embedder, judge_model=None, split=None)` | Computes the quality-grounded marginal credit via a reference-free judge, then settles. `(k+1)` generations + judge calls — batch / operator-triggered, not inline. |
| `get(message_id)` | The persisted `SettlementRecord`, or `None`. |
| `journal(session_id)` | The session's payout journal. |

Revenue is conserved (shares + treasury sum to the revenue when the split sums to 1)
and the contributor pool is quality-gated by per-answer feedback. Money is `float`
in the prototype; production hardening moves to integer minor units / `NUMERIC`.

## `GroundingService` — vote-gated retrieval

Turns a query into the **approved** grounding set for a routed category. The
governance invariant lives below the seam: only peer-approved contributions are ever
returned (vote-gated via status), so a false or superseded claim can't ground an
answer (whitepaper C7). Integrators ground against this contract without depending on
the retrieval implementation (BM25 today; pgvector/dense later).

```python
from dequorum.retrieval import Retriever
from dequorum.services import GroundingService

grounding = GroundingService(Retriever(contribution_store))
grounded = grounding.ground(query, category_id=cat, top_k=3)
proof_chain = [sc.contribution.signature for sc in grounded]
grounding.invalidate(cat)   # after a governance status change
```

| Method | Contract |
| --- | --- |
| `ground(query, *, category_id, top_k=3)` | Approved grounding set, best-first; empty when nothing approved matches. |
| `invalidate(category_id=None)` | Drop cached indexes after a status change (all categories when `None`). |

## How an external provider integrates

1. Submit / serve contributions through `knowledge` + `review` (governance).
2. **Ground** answers through `GroundingService` (vote-gated).
3. Honor the `core` proof chain (`[sc.contribution.signature ...]`).
4. **Settle** through `LedgerService` (credit + payout).

The base model and UI are theirs. See [build-direction.md](build-direction.md) for
why the product is this layer, not the model.
