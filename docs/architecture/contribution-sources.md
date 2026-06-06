# Contribution sources: how real documents become signed claims

> **Status:** v0.1 ships single-claim text submission. This doc designs the path from "paste one claim" to "ingest a repo's worth of documentation, extract claims, sign each one." The data model already supports it (see [`services/db/data-model.md`](../../services/db/data-model.md)'s `documents` and `contribution_sources` tables); the UI and the extraction pipeline are what's missing.

## The problem

Today's contribute form is a single `<textarea>` for one claim + a list of citation URLs. That works for the seed network where five hand-coded contributors are typing in five claims each. It does not work for the real network, where the typical contributor will be:

- A **library maintainer** who wants the network to know about their library — the contribution source is the project's README, docs site, or design doc.
- A **researcher** who wants the network to know their paper's findings — the source is the PDF on arXiv or in a journal.
- A **practitioner** who has accumulated notes — the source is a markdown file, a Notion export, a Google Doc, a wiki dump.
- A **company** publishing internal docs as a contribution — the source is a docs repository.

Each of these starts as **a body of text the contributor has the right to share** and ends as **a set of signed claims filed under one or more categories**. The contribute form is the bottleneck between those two states.

## The shape of a richer submission

A contribution submission becomes a two-stage flow:

1. **Source ingestion.** The contributor uploads / links a document. The system extracts candidate claims from it. The contributor reviews and edits.
2. **Per-claim publication.** Each accepted claim becomes a standard signed `Contribution` row, with a `contribution_sources` row pointing back to the document + byte span it was extracted from.

The data model already has this shape — `documents` and `contribution_sources` are in `data-model.md`'s "Planned tables (v0.2+)" section. The contribute UI is what bridges the gap.

### Stage 1 — Source ingestion

Six source types covered by one flow:

| Source | Accepted forms | Notes |
| --- | --- | --- |
| **Markdown** | `.md` upload, paste | The native format; no parsing needed |
| **PDF** | `.pdf` upload, arXiv URL | Extracted with `pypdf` + section detection; arXiv URLs auto-resolve to the PDF |
| **HTML** | URL | Fetched server-side, sanitized through `readability-lxml` for main content |
| **Source repo** | GitHub URL (`/owner/repo` or `/owner/repo/tree/<branch>/<path>`) | Pulls `README.md` + any `docs/` markdown via the GitHub API; optionally constrained by glob |
| **Plain text** | Paste, `.txt` | Fallback for everything else |
| **Notion / Google Docs** | URL with auth | v0.3+ — requires OAuth wiring for each provider; defer until there's user demand |

For each source the system records a `documents` row carrying: `(document_id, contributor_id, source_kind, source_url|file_hash, byte_count, fetched_at, signature)`. The document itself is content-hashed; the same source from two contributors gets one document row and two `documents.contributor_id` claims (which is fine — provenance is what matters, dedup is a side benefit).

#### Rights confirmation

This is the load-bearing detail. Before the document is accepted, the contributor must affirm one of:

- *"I authored this content."*
- *"This content is published under a license that permits redistribution and attribution-preserving derivative works (e.g. CC-BY, CC-BY-SA, MIT, Apache 2.0, public domain)."*
- *"I have explicit written permission from the rights holder to share this content via DeQuorum."*

The choice is recorded on the `documents` row alongside the document hash. A wrong assertion is a violation of the agreement (PRODUCT.md §contributor agreement); the network's accountability mechanism for that is the same as for plagiarized contributions — reviewer flag → triage rejection → potential tier penalty.

For source-repo and PDF sources, the system auto-detects open-source licenses (LICENSE file, arXiv metadata) and pre-fills the affirmation when it can.

### Stage 2 — Per-claim extraction + publication

The contributor sees their source rendered alongside a list of **candidate claims** the extractor produced. The interaction is closer to a triage UI than a form:

```
┌──────────────────────────────────┬─────────────────────────────────┐
│ Source                           │ Candidate claims (12)           │
│                                  │                                 │
│ # asyncio.gather and             │ ☑ asyncio.gather collects       │
│   asyncio.wait                   │   results in the order of the   │
│                                  │   awaitables…                   │
│ asyncio.gather collects results  │   ↳ category: python/async ▾    │
│ in the order of the awaitables.  │   ↳ citation: [1] [+]           │
│ Pending tasks are cancelled if   │                                 │
│ one raises…                      │ ☑ asyncio.wait returns a tuple  │
│                                  │   (done, pending) sets, with…   │
│ asyncio.wait, by contrast,       │   ↳ category: python/async ▾    │
│ returns a tuple (done, pending)  │                                 │
│ of sets and never cancels…       │ ☐ Pending tasks are cancelled…  │
│                                  │   ↳ (decline — duplicates #1)   │
│ ...                              │ ...                             │
└──────────────────────────────────┴─────────────────────────────────┘

[Publish 8 selected claims as drafts]
```

The extractor is a **best-effort LLM pass** running on the network's own base model with a fixed prompt. It produces JSON of the form:

```json
[
  {
    "claim": "asyncio.gather collects results in the order of the awaitables.",
    "category_suggestions": ["programming/python/async"],
    "source_span": { "start": 142, "end": 219 },
    "confidence": 0.91
  },
  ...
]
```

The contributor:

- Edits any claim text.
- Approves or declines each candidate (defaults to approved if confidence > 0.7).
- Confirms or overrides the suggested category.
- Optionally splits one claim into two or merges two into one.

On *Publish*, each approved claim becomes a `Contribution` row, signed client-side as today, with an attached `contribution_sources` row linking back to the `documents.document_id` + `source_span`. The result is exactly the same data shape the v0.1 single-claim flow produces, just at scale.

### Why client-side signing stays load-bearing

Even with bulk extraction, **the signing primitive is unchanged**: each claim is signed by the contributor's Ed25519 key locally. The extractor surfaces candidates; the contributor *signs* the ones they take responsibility for. This preserves the proof-chain semantic: a network reviewer downstream can verify that a specific natural-language claim was authored — and stood behind — by the holder of a specific key, regardless of whether the claim originated as a human typing or as an LLM-extracted candidate the human approved.

The signing key never leaves the browser. The extractor never produces signed content; it produces candidates. The contributor is the boundary.

## Taxonomy: who adds categories, and how

Today the seed taxonomy is code-owned (`services/app/src/dequorum/taxonomy/seeds.py`). 29 categories ship in the seed tree; 5 of them are routable (carry a persona). The seed is re-upserted on every startup, so a code change updates the live tree on the next deploy.

This works for v0.1. It doesn't scale — every new domain (medicine, law, climate, …) would require a code change. The path past code-owned taxonomy has three steps:

1. **Curator-extensible taxonomy.** Tier-3+ contributors can add a *non-routable* category (an organizational node) directly via the API. New routable leaves still require a maintainer-issued PR because a routable leaf carries a persona prompt that grounds every answer in that domain — the prompt is part of the model's behavior and shouldn't be self-serve at v0.2.

2. **Category-request workflow.** Anyone can open a category request: a short proposal for a new routable leaf (display name, slug, proposed persona, sample contributions they'd file under it). The request goes through the same triage process as a contribution. Curators approve, and the category lands on the next deploy.

3. **Self-serve routable categories with persona governance.** Eventually a routable category's persona is itself a *governed artifact* — versioned, voted on, with a lineage just like a contribution. At that point any tier-3+ contributor can propose a new routable category and the network votes on the persona text. This is the v1.x-class shape and depends on the persona being load-bearing enough that getting its wording right matters.

For v0.2 the right move is steps 1 and 2: organizational categories self-serve, routable leaves request-and-approve. The DBML already has the `categories` table; the new tables are `category_requests` (a request to add or modify a category) and an extension to the agreement covering taxonomy submissions.

### Where do categories come from initially?

The seed taxonomy at v0.1 covers programming, web/protocols, math, finance, health, humanities, etc. — 29 nodes total. None of them claim to be exhaustive. The expansion vector is:

- **Top-down for the obvious frontier.** Medicine, law, climate, education, design, cooking — domains DeQuorum has explicit pitches for. These get persona-carrying routable leaves in v0.2 as the first contributors arrive in each domain.
- **Bottom-up via category requests.** Long-tail subcategories (e.g. `cooking/fermentation/sourdough` vs the more general `cooking/fermentation`) get added when a contributor surfaces the need.
- **Reorganization by curators.** Tier-4 curators can rename, re-parent, or merge categories — but never *delete* one with contributions filed under it. Reorganization preserves contribution attribution by remapping the `primary_category_id` foreign key.

The seed isn't trying to be the final taxonomy — it's trying to be a *plausible* one that the first 100 contributors can productively start filing under.

## What needs to be built (v0.2 milestone)

In dependency order:

1. **`documents` + `contribution_sources` tables.** Schema migration. Author + signature columns; `fetched_at`; `source_kind`; `source_url`; `body_text`; `body_hash`; `byte_count`; `rights_assertion`.
2. **Document ingest endpoint.** `POST /v1/documents` with multi-source support. Fetches/parses, content-hashes, records the row.
3. **Candidate extraction.** Server-side LLM call against the network's base model with a fixed extraction prompt. Cached by document hash so re-extracting is free.
4. **Triage-UI surface for bulk submission.** Replaces today's single-claim form. Renders source alongside candidates, supports per-claim edit / accept / decline / split / merge.
5. **Client-side multi-sign.** Sign each accepted claim locally, batch-submit as a transaction; on partial failure, surface which claims didn't post and why.
6. **Category requests.** `POST /v1/category-requests` + a triage UI that matches the contribution triage flow.

The data-model.md "Planned tables" entry is consistent with what (1) needs; (6) gets a new entry there when it lands.

## What the v0.1 contribute form should do in the meantime

Until the richer flow lands, the single-claim form should grow two affordances that buy us time:

1. **A "this is a single claim from a larger document" disclosure** — a small "Source URL" field, optional, that gets stored alongside the contribution. When the documents table lands, those URLs get retro-extracted into proper `documents` rows.
2. **An obvious "Bulk contribution coming in v0.2" callout** at the top of the form with a link to this design doc, so contributors with a corpus understand the limitation isn't permanent.

Both are 30-line changes that protect the path without prejudging the design. Worth landing alongside this doc.
