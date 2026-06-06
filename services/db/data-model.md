# Data model overview

Canonical reference: [data-model.dbml](data-model.dbml) (paste into [dbdiagram.io](https://dbdiagram.io/d) to render).

## Today's tables (v0.1, in `src/dequorum/knowledge/store.py`)

| Table | Purpose |
| ----- | ------- |
| `contributions` | Signed atomic factual claims. The unit of attribution and the unit of retrieval. |
| `votes` | Signed +1/0/-1 votes on contributions. One slot per (contribution, voter). |

That's it. Two tables. Everything else in the codebase — the routable `Category` set, `AttributionLedger`, `ProofObject`, signatures, the four invariants — lives in memory or in dataclass instances. Postgres holds only what needs to persist across runs (the signed claims and votes).

> **v0.2 note:** The `Expert` / `ExpertRegistry` layer that previously held persona metadata has been collapsed into the existing `Category` taxonomy. Persona fields (`system_prompt`, `specialty_tags`, `example_questions`) now live as columns on `categories`; routing picks a routable category (one whose `system_prompt` is non-empty); contributions are addressed solely by `primary_category_id`. There is no Expert entity anywhere in the codebase. See migration `0004_categories_carry_personas`.

## Where each model class lives

The dataclasses are organized by domain, not centralized — each module owns the types it produces:

| Concept | Defined in | Notes |
| ------- | ---------- | ----- |
| `Signature` | `src/dequorum/core/node.py` | Ed25519 over canonical bytes; same shape for every signed entity |
| `ProofObject` | `src/dequorum/core/proof.py` | Ordered chain of signatures returned by every pipeline call |
| `AttributionLedger` | `src/dequorum/core/ledger.py` | In-memory today; backed by `ledger_entries` table later (see DBML) |
| `Contribution` | `src/dequorum/knowledge/contribution.py` | The atomic signed claim |
| `STATUS_*` constants | `src/dequorum/knowledge/status.py` | `pending` / `approved` / `rejected`, extracted to break import cycles |
| `ContributionStore` | `src/dequorum/knowledge/store.py` | Postgres-backed CRUD; schema in `src/dequorum/db/migrations/` |
| `Category` | `src/dequorum/taxonomy/category.py` | Taxonomy node + (since v0.2) the persona that grounds routed answers |
| `CategoryStore` | `src/dequorum/taxonomy/store.py` | Postgres-backed CRUD; `routable()` returns the persona-carrying subset |
| `Vote` | `src/dequorum/review/vote.py` | Signed vote slot |
| `ReviewService`, `ReviewOutcome` | `src/dequorum/review/service.py` | Tally + status transitions |
| `Comment`, `LineAnchor` | `src/dequorum/comments/comment.py` | Signed discussion attached to a contribution; threaded via `parent_comment_id`; append-only with soft-redaction (Phase 1 of [contribution-governance.md](contribution-governance.md)) |
| `CommentStore` | `src/dequorum/comments/store.py` | Postgres-backed CRUD over the `comments` table (migration `0003_comments`) |
| `RoutingResult`, `SelectedCategory` | `src/dequorum/routing/result.py` | Shared between both router implementations |
| `CategoryAnswer`, `NetworkResponse` | `src/dequorum/inference/pipeline.py` | The query-time output types (offline / benchmark path) |
| `BenchmarkResult`, `BenchmarkReport` | `src/dequorum/benchmark/runner.py` | Quality-check harness output |

The principle: types live next to the code that produces them. There's no central `models.py` because (a) it would conflict with the domain-grouped folder structure, and (b) any model that exists in only one module shouldn't be hoisted just for symmetry.

## Planned tables (v0.2+)

From [contributor-intake.md](../../docs/architecture/contributor-intake.md), four new tables show up the moment we move past hand-coded keypairs:

| Table | Purpose | Lands when |
| ----- | ------- | ---------- |
| `contributors` | The human/org behind a signing key. Currently `contributions.contributor_id` is a free string; this turns it into a foreign key. | first external testers join (v0.2) |
| `documents` | Source artifact for bulk submissions (uploaded markdown, PDF, URL fetch). Each document yields multiple contributions via the extraction pipeline. | first time we let someone upload more than one fact at a time (v0.3) |
| `contribution_sources` | Links a contribution back to the document + byte span it was extracted from. Citation chains resolve through this. | with `documents` |

When these arrive, they get their own Python module (likely `src/dequorum/contributors/`) following the existing one-domain-per-folder pattern.

## Late-stage tables (v1.x+)

Two tables reserve shape for things that exist in code but not in SQL today:

| Table | Why it'll exist | Why not yet |
| ----- | --------------- | ----------- |
| `reputation` | Sybil-resistant, reputation-weighted voting (required before public launch per PRODUCT.md §5) | Today votes are 1-per-account equal weight; reputation tracking is on the open-questions list |
| `ledger_entries` | Persistent ledger of revenue distributions per query | Today `AttributionLedger` is in-memory — only persists after we have real revenue to distribute |

## What stays the same regardless of stage

Every signed entity — `Contribution`, `Vote`, `Document`, future credentials — uses the **same `Signature` primitive** from `core/node.py`. The proof chain shape never changes; it just gets richer ("contribution X extracted from page 47 of document Y by contributor Z" vs today's "contribution X by contributor Y in category Z").

Every signed entity is **content-addressable** by a deterministic hash, computed from canonical JSON bytes. Same content → same id, always. That's what makes idempotent submission, signature verification, and audit possible.

The four invariants (reproducibility, full provenance, explicit failure, compositional locality) apply to every layer of the data model — including the planned ones.

## Updating this doc

When you add a real new table or rename one, edit both:
- [`data-model.dbml`](data-model.dbml) (the canonical schema, sibling of this file)
- This file's tables-list section

When you add a new dataclass to the codebase, just update the "Where each model class lives" table here so future-you can find it.
