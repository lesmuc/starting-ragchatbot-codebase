#!/usr/bin/env bash
# quality.sh — run code quality checks for the RAG chatbot backend
#
# Usage:
#   ./scripts/quality.sh          # auto-format all Python files (default)
#   ./scripts/quality.sh --check  # check formatting without making changes (CI mode)
#   ./scripts/quality.sh --help   # show this help

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
MODE="format"

for arg in "$@"; do
  case "$arg" in
    --check) MODE="check" ;;
    --help)
      echo "Usage: $0 [--check] [--help]"
      echo ""
      echo "Options:"
      echo "  (none)   Auto-format all Python files with black"
      echo "  --check  Verify formatting without changing files (exit 1 if issues found)"
      echo "  --help   Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

echo "==> Running black on $BACKEND_DIR"

if [ "$MODE" = "check" ]; then
  echo "    Mode: CHECK (no files will be modified)"
  uv run black --check "$BACKEND_DIR"
else
  echo "    Mode: FORMAT (files will be reformatted in place)"
  uv run black "$BACKEND_DIR"
fi

echo ""
echo "==> Quality checks passed."
