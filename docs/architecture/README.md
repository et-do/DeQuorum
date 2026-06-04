# Architecture docs

Design notes that live longer than a single feature. If you're trying to understand how DeQuorum is wired together, start here.

| Doc | What it covers |
| --- | -------------- |
| [data-model.md](data-model.md) | Overview of every entity in the system, where each dataclass lives, and what's planned vs in-code today |
| [data-model.dbml](data-model.dbml) | Canonical schema in DBML — paste into [dbdiagram.io](https://dbdiagram.io/d) to render the ERD |
| [contributor-intake.md](contributor-intake.md) | How signup → agreement → credentials → bulk document submission will work as we scale past hand-coded keypairs |
| [model-swap.md](model-swap.md) | One-constant procedure for swapping the network's base LLM; license purity rule; registry entry contract |
| [services-roadmap.md](services-roadmap.md) | Sequenced plan for new services (worker, ledger, GCS, Redis), production gotchas, language choices, CI/hooks summary |
| [devenv-setup.md](devenv-setup.md) | One-time setup checklist for a fresh clone or devcontainer rebuild — verifies all pre-commit hooks + CI workflows are token-free |
| [cost-model.md](cost-model.md) | Back-of-envelope economics at 1000 users — GCP infra spend, marketplace flows, per-role earnings, where the model breaks |

For product-level vision (who it's for, what it does, pricing, etc.) see [../PRODUCT.md](../PRODUCT.md).

For research notes and literature reviews, see [../research/](../research/).
