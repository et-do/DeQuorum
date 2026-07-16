# Public API and client SDKs

> **Status:** v0.1 is HTTP API only. SDKs are scheduled for v0.2 once the API contract has stabilized through internal usage. This document defines the target architecture so the scaffolding lands in the right shape.

The question this doc answers: *can a third-party developer `pip install` something and integrate DeQuorum into their own app?* Yes — by design — and the architecture for that integration is described below.

## What an external integrator needs

There are three integration shapes a third party might want, in increasing depth:

1. **Ask the network a question.** Get a grounded answer back, stream it to the user. Same UX surface as ChatGPT/Claude's developer API: the integrator calls one method and gets text + attribution metadata.
2. **Embed the network's contribution surface.** A platform that already has authenticated users (Discord bot, documentation site, internal tool) wants to let those users *contribute* and *vote* without leaving the platform. The SDK exposes the contribution and voting endpoints with the platform's identity bridged in.
3. **Run an integrator-side host node.** Companies that need on-prem inference for compliance reasons can run their own compute, but still participate in the network's contribution pipeline. This is a separate "operate a node" deployment, documented in the services-roadmap.

This doc focuses on shapes 1 and 2 — the developer SDK. Shape 3 is the "host your own DeQuorum instance" path covered by [services-roadmap.md](services-roadmap.md).

## Why HTTP, not an embeddable library

It would be tempting to ship a fat library that includes the base model, the retrieval pipeline, and a local Postgres — `dequorum.local()` and the developer never makes a network call. Tempting and wrong:

- **It would fork the contribution corpus.** A library running locally couldn't participate in voting, lineage, or payout — it would just be a local RAG implementation that *happens* to share the data shape. Users would get answers but the network wouldn't get attribution, and contributors wouldn't get paid.
- **It would freeze the model.** Every integrator's app would ship whatever base model + LoRA snapshot we packaged at the time, with no way to receive updates as the contribution corpus grows.
- **It would bypass governance.** The whole point of DeQuorum is *peer-reviewed* answers; a local mode would have no peers.

The right architecture is the same shape OpenAI / Anthropic / Mistral chose: a stable HTTP/JSON API at the boundary, with thin language-specific client libraries that wrap it. The network stays canonical; integrators get a clean SDK.

## API contract — what's stable

The `/v1/*` endpoints are the public surface. Today they're:

| Endpoint | Purpose | Stable? |
| --- | --- | --- |
| `POST /v1/chat/sessions` | Create a chat session | ✅ |
| `GET  /v1/chat/sessions` | List sessions for the authenticated user | ✅ |
| `POST /v1/chat/sessions/{id}/stream` | NDJSON-streamed chat turn | ✅ |
| `GET  /v1/chat/sessions/{id}` | Fetch session + messages | ✅ |
| `DELETE /v1/chat/sessions/{id}` | Delete a session | ✅ |
| `PATCH /v1/chat/sessions/{id}` | Rename a session | ✅ |
| `POST /v1/chat/sessions/{id}/messages/{mid}/feedback` | Rate a network answer (±1) — quality signal for payout | ✅ |
| `GET  /v1/contributions` | List approved contributions (filterable) | ✅ |
| `POST /v1/contributions` | Submit a contribution | ✅ |
| `GET  /v1/contributions/{id}` | Fetch contribution + signature chain | ✅ |
| `POST /v1/contributions/{id}/votes` | Cast a vote | ✅ |
| `GET  /v1/contributions/{id}/comments` | Threaded discussion | ✅ |
| `POST /v1/contributions/{id}/comments` | Post a comment | ✅ |
| `GET  /v1/contributors` | List contributors (paginated) | ✅ |
| `GET  /v1/contributors/{id}` | Contributor profile + their contributions | ✅ |
| `GET  /v1/categories` | The full taxonomy tree | ✅ |
| `GET  /v1/lineages/{id}` | One claim's version history | ✅ |
| `POST /v1/settlements/{mid}` | **Operator:** trigger faithful settlement of an answer (enqueues off-hot-path) | ✅ |
| `GET  /v1/settlements/{mid}` | **Operator:** read an answer's persisted payout (audit boundary) | ✅ |
| `POST /v1/worker/settle` | **Operator/worker:** process one settlement job (Cloud Tasks delivery target) | ✅ |

The `/v1` prefix is the stability contract. Any breaking change moves to `/v2`; the old surface stays alive for a deprecation window so SDKs don't break their consumers overnight.

## Authentication

Every request carries `Authorization: Bearer <token>`. Today the token is a Firebase ID token; the auth layer is wrapped behind a small `dequorum.auth` module so swapping to a different provider (or issuing instance-native tokens) is a one-file change. SDK consumers never see the underlying token shape — they pass an `api_key` or call the SDK's auth helpers.

Two token classes are planned:

- **End-user tokens.** Bound to an authenticated contributor identity. Used for chat, voting, submitting.
- **Service tokens.** Bound to an integrator app. Used for backend-to-backend traffic (e.g., a bot that asks questions on behalf of users). Service tokens carry the *integrator's* identity, not the end user's; chat-session ownership is recorded against the integrator's contributor id.

The **settlement / worker endpoints** are a separate, operator-only plane: they
carry `X-Operator-Key: <DEQUORUM_OPERATOR_API_KEY>` (not a user token) and are
disabled (503) until that key is configured, so the money path can never be
triggered by an end-user token. In production Cloud Tasks forwards the key on each
delivery; OIDC verification is the eventual upgrade. See
[protocol-services.md](protocol-services.md) for the settlement flow.

Rate limits, billing, and per-token usage attribution all key off the token. A signed answer's proof chain includes the operator's signature, which in the SDK case is the operator of the DeQuorum instance the SDK is calling — not the SDK consumer.

## Client SDKs

Two shipping targets at v0.2:

### Python — `dequorum-client`

```python
from dequorum_client import DeQuorum

dq = DeQuorum(api_key="dq_live_…")

# One-shot question (collects the full streamed answer).
answer = dq.chat.ask("What's the difference between asyncio.gather and asyncio.wait?")
print(answer.text)
for cite in answer.citations:
    print(f"  ↳ {cite.contributor_display_name} — {cite.contribution_id}")

# Streaming chat.
session = dq.chat.create_session()
for event in dq.chat.stream(session.id, "How does HTTP/3 transport work?"):
    if event.kind == "chunk":
        print(event.text, end="", flush=True)
    elif event.kind == "done":
        for cite in event.response.citations:
            print(f"\n[{cite.contributor_display_name}]")

# Contribute (signed locally, posted to the network).
key = dq.identity.signing_key  # loaded once, persisted in the client config
draft = dq.contributions.draft(
    category_id="programming/python/typing",
    text="Generator[Y, S, R] annotates yield, send, return.",
    citations=["https://peps.python.org/pep-0492/"],
)
posted = dq.contributions.submit(draft, signing_key=key)
```

Implementation: a thin wrapper around `httpx` (sync + async clients). NDJSON streaming uses `httpx`'s `iter_lines`. Signatures are produced locally via `pynacl` so the network never sees the contributor's signing key. Distributed via PyPI.

### TypeScript / JavaScript — `@dequorum/client`

Same surface area, browser- and Node-compatible. Uses `fetch` (no extra deps in browsers) and `ReadableStream` for NDJSON. Distributed via npm. Ships ESM by default.

```ts
import { DeQuorum } from "@dequorum/client";

const dq = new DeQuorum({ apiKey: "dq_live_…" });

for await (const event of dq.chat.stream(sessionId, "...")) {
    if (event.kind === "chunk") process.stdout.write(event.text);
}
```

### Code generation strategy

Both clients are generated from the same source of truth: the FastAPI app already produces an OpenAPI 3.1 schema at `/openapi.json`. The SDKs use:

- **Python:** `openapi-python-client` (regenerates `dequorum_client/api/`) + a hand-written ergonomic façade (`DeQuorum`, `Session`, `Answer`, etc.) that calls the generated client.
- **TypeScript:** `openapi-typescript` for types + a hand-written façade matching the Python one.

The façade is what most users touch. The generated client is the seam that keeps both SDKs in sync with the API automatically.

## Streaming format

The NDJSON event stream for `/v1/chat/sessions/{id}/stream` is the most-important contract because it's the only one used during normal request flow. Event shapes:

```json
{"stage": "thinking"}
{"stage": "drawing_from_contributors"}
{"stage": "answering"}
{"chunk": "Hello"}
{"chunk": " world."}
{"done": { "query": "...", "routing": {...}, "experts": [...], "final_answer": "...", "ledger": {...} }}
{"title": "Asyncio gather vs wait"}
{"error": "rate-limited"}
```

Order guarantees:
- At most one `stage:*` event per stage transition.
- Multiple `chunk:*` events; concatenation reconstructs the final answer text.
- Exactly one `done:*` event at the end of a successful stream.
- An optional `title:*` event after `done:*` if the session was auto-titled.
- At most one `error:*` event; if it appears, no `done:*` follows.

SDKs expose this as a typed event union. Consumers that want one-shot replies call `chat.ask(...)` which accumulates internally and returns once `done` arrives.

## What's needed before v0.2 SDKs ship

1. Pin the OpenAPI schema and add a generated-snapshot CI check so any API change shows up in the diff.
2. Lock down the `done` payload's `experts` shape — that key still carries the old terminology in the field name; either rename it to `citations` (with a v1 alias) or commit to keeping the name as an SDK-visible word. (The user-facing chat UI doesn't render this field; the only consumer of the post-rename name will be the SDK.)
3. Stand up an API-key system distinct from end-user Firebase tokens. Storage + revocation surface live behind `/v1/api-keys`.
4. Publish a small versioning policy: how long deprecated endpoints stay alive, how breaking changes are signaled, what counts as a breaking change.

These are tracked in [services-roadmap.md](services-roadmap.md) under the v0.2 milestone.

## Why not a CLI

There already is one — `dequorum` in `services/app/` — but it's an operator tool (start the server, run benchmarks, seed the DB), not an end-user surface. A `dequorum-cli` for end users is an obvious natural follow-on once the Python SDK exists: it would be a 200-line wrapper. Not a v0.2 priority.

## Summary

- DeQuorum's external integration surface is the `/v1/*` HTTP API. The contract is stable; breaking changes go to `/v2`.
- Two SDKs land at v0.2: Python (`dequorum-client`) and TypeScript (`@dequorum/client`), both generated from OpenAPI and wrapped in an ergonomic façade.
- Signatures are produced client-side via Ed25519; the network never sees a contributor's signing key.
- Embedding the network in a third-party app is shape #2; running a separate inference node is shape #3; both reuse the same HTTP contract.

This architecture means the answer to *"can I integrate DeQuorum into my app?"* is *yes, with one import and one API key*, while preserving the network's contribution pipeline, governance, and payout flow as the load-bearing system properties.
