# services/ollama

Local Ollama instance that serves the DeQuorum network's base LLM.

Pulls `${OLLAMA_BOOTSTRAP_MODEL}` (set by compose) on first start. The model
weights persist in a named docker volume (`ollama-models`) so subsequent
restarts are instantaneous.

## Swap the base model

This service's bootstrap model is wired to the central registry in
[`services/app/src/dequorum/inference/models.py`](../app/src/dequorum/inference/models.py):

- `OLLAMA_BOOTSTRAP_MODEL` in [`compose.yml`](../../compose.yml) should match
  the `ollama_tag` of whichever profile is `DEFAULT_BASE_MODEL_ID`.
- After changing the default in the registry, update compose.yml and run
  `docker compose up ollama --build`.

See [`docs/architecture/model-swap.md`](../../docs/architecture/model-swap.md)
for the full swap procedure.
