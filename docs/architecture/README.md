# Architecture docs

Design notes that live longer than a single feature. If you're trying to understand how DeQuorum is wired together, start here.

| Doc | What it covers |
| --- | -------------- |
| [build-direction.md](build-direction.md) | Decision record: how the whitepaper §8 findings drive product/protocol design — component changes (no pivot), invent-vs-integrate, protocol seams, platform→protocol sequencing, work plan |
| [services/db/data-model.md](../../services/db/data-model.md) | Overview of every entity in the system, where each dataclass lives, and what's planned vs in-code today |
| [services/db/data-model.dbml](../../services/db/data-model.dbml) | Canonical schema in DBML — paste into [dbdiagram.io](https://dbdiagram.io/d) to render the ERD |
| [contributor-intake.md](contributor-intake.md) | How signup → agreement → credentials → bulk document submission will work as we scale past hand-coded keypairs |
| [model-swap.md](model-swap.md) | One-constant procedure for swapping the network's base LLM; license purity rule; registry entry contract |
| [contribution-governance.md](contribution-governance.md) | Triage → vote → live lifecycle; comments + edit-request data model; phased plan to evolve the current single-stage flow |
| [retrieval-and-scaling.md](retrieval-and-scaling.md) | Why pure vector search won't scale; three-tier route → retrieve → train roadmap; what to land now vs. plan for |
| [api-and-sdk.md](api-and-sdk.md) | Public `/v1` surface, planned Python + TypeScript SDKs, OpenAPI-generated client strategy, why HTTP not embeddable |
| [contribution-sources.md](contribution-sources.md) | Path from single-claim form to bulk document ingestion: source kinds, rights confirmation, candidate extraction, multi-sign UX, taxonomy growth strategy |
| [gpu-and-throughput.md](gpu-and-throughput.md) | How to verify Ollama is actually on the GPU; three fix paths (WSL2 host install, smaller model, ROCm passthrough); tuning checklist |
| [services-roadmap.md](services-roadmap.md) | Sequenced plan for new services (worker, ledger, GCS, Redis), production gotchas, language choices, CI/hooks summary |
| [devenv-setup.md](devenv-setup.md) | One-time setup checklist for a fresh clone or devcontainer rebuild — verifies all pre-commit hooks + CI workflows are token-free |
| [cost-model.md](cost-model.md) | Back-of-envelope economics at 1000 users — GCP infra spend, marketplace flows, per-role earnings, where the model breaks |

For product-level vision (who it's for, what it does, pricing, etc.) see [../PRODUCT.md](../PRODUCT.md).

For the long-form architectural / economic argument intended for an external audience, see the [whitepaper](../WHITEPAPER.md). The same prose backs the in-browser `/whitepaper` page; keep both files in sync when editing.

For research notes and literature reviews, see [../research/](../research/).
