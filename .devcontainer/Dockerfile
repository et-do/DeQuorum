# Thin orchestration host for the DeQuorum dev environment.
#
# All language runtimes (Python, Node) and inference (Ollama) live in their
# own service containers in compose.yml. This host only needs the docker CLI
# (provided by the docker-in-docker feature in devcontainer.json), git, and
# pre-commit. It exists to host the repo, run pre-commit, and `docker compose`.

FROM mcr.microsoft.com/devcontainers/base:debian
