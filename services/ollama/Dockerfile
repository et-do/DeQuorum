# Local LLM inference server for DeQuorum.
#
# Production target: depends on the model size. 7B-class fits comfortably on
# a Cloud Run instance with a GPU; larger models go to a dedicated VM with a
# discrete GPU. The image is identical; the runtime substrate changes.

FROM ollama/ollama:latest

# Pull the default base model on first start, then exec into ollama serve.
# `entrypoint.sh` is idempotent — re-running it on subsequent starts skips
# the pull because the named volume persists the model weights.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
