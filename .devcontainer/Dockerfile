FROM mcr.microsoft.com/devcontainers/python:3.13

# Ollama: local LLM server. Installed via official script (detects platform, drops binary in /usr/local/bin).
# The systemd-service warning during install is expected and irrelevant inside a container.
# zstd is required by the install script to extract the release archive.
RUN apt-get update \
    && apt-get install -y --no-install-recommends zstd \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://ollama.com/install.sh | sh

# Pre-create the model cache dir with correct ownership so the named volume mount works cleanly.
RUN mkdir -p /home/vscode/.ollama && chown -R vscode:vscode /home/vscode/.ollama
