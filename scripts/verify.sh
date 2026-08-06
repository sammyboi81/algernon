#!/usr/bin/env bash
# One command to reproduce Algernon's frugality benchmark with ZERO paid keys.
# Defaults to your local ollama (llama3.2:3b). A skeptic runs this and gets the
# same pattern of numbers.
#
#   ./scripts/verify.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

# Ensure the one runtime dep for the benchmark (httpx) is importable.
python -c "import httpx" 2>/dev/null || python -m pip install --quiet "httpx>=0.27"

# Friendly preflight for the free local worker.
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "NOTE: local ollama not reachable at 127.0.0.1:11434."
  echo "  Install from https://ollama.com then run:  ollama pull llama3.2:3b"
  echo "  (Or set ANTHROPIC_API_KEY / OPENAI_API_KEY to benchmark a paid provider.)"
fi

exec python -m benchmark
