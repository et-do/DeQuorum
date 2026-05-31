# Contributor Intake — Design Notes

> **Status:** forward-looking sketch. Today's intake = single signed claims via CLI/web. This doc plans how that evolves to bulk submission as DeQuorum scales.

## The shape of contributor signup at scale

The flow the product needs to support eventually:

```
1. Sign up                  -> account + signing keypair generated
2. Sign user agreement       -> attestation that submissions are theirs or public-domain
3. Provide credentials       -> optional W3C Verifiable Credentials (signal, not gate)
4. Add documents/facts/info  -> bulk intake: paste, upload, URL, structured form
                              -> system splits into atomic claims
                              -> contributor picks expert persona(s) to attribute under
                              -> claims enter the per-claim review queue
```

Today only step 4 partially exists — and only as a one-claim-at-a-time form. Steps 1-3 are vestigial (we use a hardcoded keypair per expert). The roadmap below covers steps 1-3 and the bulk version of step 4.

## What we keep regardless

These primitives are good and don't change:
- **`Contribution`** — signed atomic factual claim with citations, content-addressed by `contribution_id`. The unit of attribution.
- **`Vote`** — signed +1/0/-1 from one voter on one contribution.
- **`ContributionStore`** — SQLite-backed store of contributions, votes, status.
- **`ReviewService`** — vote tally + status transitions.
- **`AttributionLedger`** — tracks who's owed how much.

These get *wrapped* by new layers, not replaced.

## New entities to add (in priority order)

### `Contributor` (the human/org behind the signing key)

Today: `Contribution.contributor_id` is just a string that happens to equal `expert_id`. That conflates the *who* with the *which persona*.

Tomorrow:
```python
@dataclass(frozen=True, slots=True)
class Contributor:
    contributor_id: str           # stable handle, e.g. "did:web:janedoe.com" or "dq:42"
    display_name: str             # human-facing
    public_key: bytes             # Ed25519 verification key
    agreement_version: str        # which TOS version they signed
    agreement_signed_at: int      # epoch seconds, signed by their key
    credentials: tuple[Credential, ...]  # optional W3C VCs, see below
```

A contributor publishes under one or more `Expert` personas. (A doctor might publish under both `medical-cardiology` and `medical-rehab`.) Or they create their own expert persona.

### `Credential` (optional, late-stage)

W3C Verifiable Credential reference. Signal-only — never a gate to participation. Used by the voting/reputation system to weight expertise signals.

```python
@dataclass(frozen=True, slots=True)
class Credential:
    credential_id: str            # VC id
    issuer_did: str               # who issued it (e.g., a medical board's DID)
    credential_type: tuple[str, ...]  # ["VerifiableCredential", "MedicalLicense"]
    proof_jwt: str                # the signed VC itself
```

Verified at submission time (signature check + issuer trust check); stored as opaque proof. The voting UI surfaces the credential type as a badge ("MD verified by State Medical Board") so reviewers can weight accordingly.

### `Document` (the source of bulk submissions)

When a contributor uploads a PDF, markdown file, or pastes a long article:

```python
@dataclass(frozen=True, slots=True)
class Document:
    document_id: str              # content-hash of the raw bytes
    contributor_id: str
    title: str
    source_uri: str | None        # e.g. https://example.com/paper.pdf or None for paste
    media_type: str               # "text/markdown", "application/pdf", etc.
    raw_bytes_digest: str         # so we can verify the original
    submitted_at: int
    signature: Signature
```

The document itself doesn't enter inference — it's the *chunks* (extracted atomic facts) that become `Contribution`s. The `Document` exists so:
1. We can show "this fact came from page 47 of `Document X`"
2. Citation chains can resolve back to a verifiable original
3. The contributor can update the source and have all derived contributions re-flow

### `Contribution.source` extension

```python
@dataclass(frozen=True, slots=True)
class ContributionSource:
    document_id: str | None       # if extracted from a Document
    span: tuple[int, int] | None  # byte offset in the original (for diffing)
    extraction_method: str        # "manual", "llm-suggested", "structured-form"
```

Not part of `contribution_id` (so dedup works); stored alongside.

## The bulk intake pipeline

Contributor uploads `mypaper.md`. What happens:

```
Upload
  -> Document stored, signed by contributor
  -> Extract: split into proposed atomic claims (~1-3 sentences each)
       (heuristics first: sentence segmentation + filters;
        LLM-assisted second: "rewrite each paragraph as N standalone claims with citations")
  -> For each proposed claim:
       a) Suggest 1-3 candidate experts (embedding similarity to expert profiles)
       b) Check for duplicates against existing approved contributions
       c) Show preview to contributor with edit/skip/approve per claim
  -> Contributor confirms per-claim (or bulk-confirms with one click)
  -> Each confirmed claim becomes a signed Contribution with status=pending
  -> Enters review queue normally; voting works exactly as today
```

Key UX principle: **the contributor is always in the loop for what gets signed in their name.** No silent auto-extraction that becomes their signed claim. The LLM-assisted extraction is a *proposal* the contributor accepts, edits, or rejects.

## Submission surface area (UX shapes to support)

Different contributors will want different intake surfaces. The data model above supports all of them through the same `Document → claims` pipeline:

| Surface | Best for | Implementation priority |
| ------- | -------- | ----------------------- |
| **Paste plain text** | Quick contributions, drafts | already there, just needs polishing |
| **Upload markdown** | Wiki authors, technical writers | medium |
| **Upload PDF** | Academic papers, books, manuals | medium — needs PDF text extraction |
| **Paste a URL** | "I want to contribute facts from this article" — system fetches + processes | medium |
| **Structured form** | Domain-specific schemas, e.g. "drug name / interaction / source" | low — vertical-specific |
| **API submission** | Org-scale integrations, e.g. a publisher pushing their archive | late-stage |
| **GitHub-style PR** | Code-knowledge contributors used to that flow | optional vertical |

## What changes for the orchestrator

- **New SQL tables**: `contributors`, `documents`, optional `credentials`. The existing `contributions` and `votes` tables stay as-is, with `contributions.contributor_id` now FK'ing to `contributors`.
- **New FastAPI endpoints**:
  - `POST /contributors` (signup) → returns contributor_id + keypair (or accepts contributor-provided public key)
  - `POST /agreements/:version/sign` → records signed agreement
  - `POST /credentials` → register a Verifiable Credential
  - `POST /documents` → upload bulk source content
  - `POST /documents/:id/extract` → run claim extraction
  - `GET  /documents/:id/proposed-claims` → list extracted claims for confirmation
  - `POST /documents/:id/confirm-claims` → accept N proposed claims as signed Contributions
- **New web pages**:
  - `/onboarding` (signup + agreement + optional credentials, all in one flow)
  - `/contribute` (replaces simple `submit` form: lets you paste / upload / URL)
  - `/documents/<id>/review-proposed` (the per-claim accept/edit/reject UI)

## What stays the same

- **Signing primitives** (`Ed25519`, `Signature`, `ProofObject`) — every layer is signable
- **Voting + review** — votes still happen per-`Contribution`, not per-`Document`
- **Attribution ledger** — distributes credit per contribution as today
- **Pipeline** (route → retrieve → invoke → compose → sign) — completely unchanged
- **The proof chain in every answer** — gains richer provenance ("contribution X from page 47 of document Y by contributor Z") but the structure is the same

## Sequencing

Rough order in which these come in:

| Phase | What ships | When |
| ----- | ---------- | ---- |
| **Now (v0.1)** | Single-claim CLI/web submission, hardcoded expert keys | done |
| **v0.2** | `Contributor` entity + signup + agreement signing (no bulk yet) | when first external testers join |
| **v0.3** | Paste-text-then-extract (one-document bulk via paste); contributor confirms per-claim | as soon as external testers want to submit more than one fact at a time |
| **v0.4** | File upload (md, txt), URL fetch | shortly after |
| **v0.5** | PDF extraction, structured forms | later |
| **v1.0** | W3C VC integration, full credential UI | per the existing late-stage roadmap |

## Open questions to revisit when we build this

- How do we prevent abuse (someone uploading copyrighted books and claiming public domain)? Document-level audit, possibly DMCA-style takedown system.
- Should `Document` itself be reviewable (votes on whether the source is reliable)? Probably yes for high-stakes domains, optional elsewhere.
- How granular should claim extraction get? One claim per sentence may over-fragment; one per paragraph may be too coarse. Test empirically.
- LLM-assisted extraction means we're using an LLM to produce content that another LLM will later use — risk of compounding errors. Need to be careful about which model does extraction and how confidence is propagated.
