#!/usr/bin/env bash
# Install Ollama (Beru's deep brain) and pull the default model.
# macOS: uses Homebrew. Linux/Windows: install from https://ollama.com first, then run:
#   ollama pull llama3.2:3b

set -euo pipefail

MODEL="${BERU_OLLAMA_MODEL:-llama3.2:3b}"

if ! command -v ollama >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    echo "Installing Ollama via Homebrew..."
    brew install ollama
  else
    echo "Ollama not found. Install from https://ollama.com then re-run this script."
    exit 1
  fi
fi

if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
  echo "Starting Ollama service..."
  brew services start ollama || true
  sleep 2
fi

echo "Pulling model: ${MODEL} (this may take a few minutes)..."
ollama pull "${MODEL}"

echo "Checking Ollama API..."
if curl -sf http://localhost:11434 >/dev/null; then
  echo "Deep brain ready at http://localhost:11434 (model: ${MODEL})"
else
  echo "Ollama installed but API not up yet. Run: ollama serve"
  echo "Then: ollama pull ${MODEL}"
fi
