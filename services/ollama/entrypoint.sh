#!/bin/sh
# Start `ollama serve`, wait for it to be ready, then pull the configured
# default base model. The default model id is set by the `OLLAMA_BOOTSTRAP_MODEL`
# environment variable (passed through from compose so it stays in sync with
# the DeQuorum model registry's DEFAULT_BASE_MODEL_ID).
set -e

BOOTSTRAP_MODEL="${OLLAMA_BOOTSTRAP_MODEL:-qwen2.5-coder:7b}"

echo "[entrypoint] starting ollama serve in background..."
ollama serve &
OLLAMA_PID=$!

# Wait for the server to accept connections.
echo "[entrypoint] waiting for ollama to be ready..."
for i in $(seq 1 30); do
    if ollama list > /dev/null 2>&1; then
        echo "[entrypoint] ollama is ready"
        break
    fi
    sleep 1
done

# Pull the bootstrap model if it isn't already present. Idempotent — ollama
# pull is a no-op if the model is up to date.
echo "[entrypoint] ensuring model '${BOOTSTRAP_MODEL}' is pulled..."
ollama pull "${BOOTSTRAP_MODEL}" || echo "[entrypoint] WARN: model pull failed; continuing without it"

# Hand control to the long-running ollama serve.
echo "[entrypoint] handing control to ollama serve (pid ${OLLAMA_PID})"
wait $OLLAMA_PID
