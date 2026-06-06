# GPU passthrough and inference throughput

How to tell whether Ollama is actually using your GPU, and what to do when it isn't. This is the most common cause of "responses take 10 minutes" — Ollama silently fell back to CPU.

## Diagnose first

The app exposes `GET /v1/inference/diag`. Hit it:

```bash
curl -s http://localhost/api/v1/inference/diag | jq
```

The signal you care about is **`ps.models[].size_vram`**:

| size_vram | Means | TTFT (7B Q4) | Throughput |
| --- | --- | --- | --- |
| `> 0` | Model is on GPU | ~150–500 ms | ~30–60 tok/s |
| `0` | Model fell back to CPU | ~2 s | ~3–8 tok/s |

The `timing.chars_per_sec` reading in the same response confirms it. Under ~10 chars/sec, you're on CPU.

## The local stack situation

The `compose.yml` `ollama` service uses `ollama/ollama:latest` and has **no GPU passthrough configured**. That's intentional for portability — the same image works on a Mac, a CI runner, a Linux box without a GPU — but it means **the default local stack runs everything on CPU**.

There are three ways to fix this, in order of effort:

### Option 1 — Run Ollama on the Windows host (recommended for WSL2 + AMD)

WSL2 + AMD + Docker GPU passthrough is currently a multi-day debug session that often ends in tears. The cleanest path:

1. Install [Ollama for Windows](https://ollama.com/download/windows). It uses the native AMD drivers and gets full RX 6700 XT throughput.
2. In a Windows terminal: `ollama pull qwen2.5-coder:7b`
3. Verify: `ollama ps` shows the model with non-zero VRAM use.
4. In WSL/Docker, point the app at the host Ollama:

   ```yaml
   # compose.override.yml
   services:
     app:
       environment:
         DEQUORUM_OLLAMA_HOST: "http://host.docker.internal:11434"
   ```

5. Drop the in-compose `ollama` service from your local stack (or leave it idle).
6. Re-run `curl /v1/inference/diag` — `size_vram` should now be ~5 GB.

Expected: TTFT ~200 ms, throughput ~50 tok/s, a 600-char answer in under 2 seconds.

### Option 2 — Smaller model, accept CPU

Use the 3B coder model as the default until GPU is sorted. ~25 tok/s on a modern CPU; a 600-char answer in ~3 seconds. Quality drop is real but not catastrophic.

```yaml
# compose.override.yml
services:
  ollama:
    environment:
      OLLAMA_BOOTSTRAP_MODEL: "qwen2.5-coder:3b"
  app:
    environment:
      DEQUORUM_OLLAMA_MODEL: "qwen2.5-coder-3b"
```

### Option 3 — ROCm passthrough into Docker on native Linux

Only do this if you're on a real Linux box (not WSL2). The `ollama/ollama:rocm` image + AMD device nodes:

```yaml
ollama:
  image: ollama/ollama:rocm
  devices:
    - /dev/kfd
    - /dev/dri
  group_add:
    - video
    - render
  environment:
    HAS_OVERRIDE_GFX_VERSION: "10.3.0"  # for RDNA2 (RX 6000-series)
```

On WSL2 this currently does not work for AMD GPUs (Microsoft has not surfaced `/dev/kfd` to WSL the way they do for NVIDIA). Don't burn a weekend trying.

## Production target

In production, the app reaches a managed Ollama instance (or any OpenAI-compatible inference endpoint) over `DEQUORUM_OLLAMA_HOST`. The compose `ollama` service is a dev convenience, not a model of the deployed topology — see [services-roadmap.md](services-roadmap.md) for the deployed inference path.

## Throughput-tuning checklist (assuming GPU is working)

Once VRAM is non-zero, response time scales with three things:

1. **Context length sent to the model.** Larger augmented system prompts = longer prefill = higher TTFT. With our 3-contribution retrieval default and short user queries, prefill is usually 500–1500 tokens (sub-second). If you bump `retrieve_top_k` past ~8 or contributions get long, watch this number.
2. **Generation length.** This is the dominant cost for actual answers. A 4000-char answer at 50 tok/s is ~20 seconds; at 6.8 tok/s it's ~2 minutes.
3. **Quantization.** Q4_K_M is the default in our registry and is the right tradeoff. Q8 doubles VRAM use for a small quality bump; Q5_K_M is a middle ground if you have headroom.
