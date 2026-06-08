#!/usr/bin/env bash
# Full setup after git clone (Python deps + Ollama deep brain).
# Usage: ./scripts/setup_machine.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Beru: Python environment ==="
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p models data

echo ""
echo "=== Beru: Deep brain (Ollama) ==="
bash "$ROOT/scripts/install_deep_brain.sh"

echo ""
echo "=== Done ==="
echo "Optional: fine-tune local GPT-2 weights (not required for chat/API):"
echo "  source .venv/bin/activate && python3 beru.py finetune"
echo ""
echo "Run API:  source .venv/bin/activate && python3 beru_api.py"
echo "Run chat: source .venv/bin/activate && python3 beru.py chat"
