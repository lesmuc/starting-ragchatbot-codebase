# Code Quality Tooling — Changes

> Note: This feature adds Python code quality tooling (black formatter) to the backend
> development workflow, not frontend changes. Documented here per skill convention.

## What Was Added

### 1. `pyproject.toml` — black as a dev dependency

Added a `[dependency-groups]` section with `black>=24.0` and a `[tool.black]`
configuration block:

```toml
[dependency-groups]
dev = [
    "black>=24.0",
]

[tool.black]
line-length = 88
target-version = ["py313"]
```

- `line-length = 88` is black's default; made explicit so editors and CI agree.
- `target-version = ["py313"]` matches the project's `requires-python = ">=3.13"`.
- Install dev dependencies with: `uv sync --group dev`

### 2. `scripts/quality.sh` — quality check script

New executable script at `scripts/quality.sh` with two modes:

| Command | Effect |
|---|---|
| `./scripts/quality.sh` | Auto-format all files in `backend/` (default) |
| `./scripts/quality.sh --check` | Check only — exits 1 if any file needs reformatting (CI mode) |
| `./scripts/quality.sh --help` | Show usage |

### 3. Formatted 11 backend Python files

Black was applied to the entire `backend/` directory. Files reformatted:

- `backend/app.py`
- `backend/ai_generator.py`
- `backend/config.py`
- `backend/document_processor.py`
- `backend/models.py`
- `backend/rag_system.py`
- `backend/search_tools.py`
- `backend/session_manager.py`
- `backend/vector_store.py`
- `backend/tests/test_ai_generator.py`
- `backend/tests/test_rag_system.py`

Typical changes made by black: consistent double-quote strings, trailing commas in
multi-line structures, normalised blank lines between definitions, and line-length
enforcement at 88 characters.

## How to Use

```bash
# One-time setup (install black into the project venv)
uv sync --group dev

# Auto-format before committing
./scripts/quality.sh

# CI / pre-commit check (no file changes, non-zero exit on failure)
./scripts/quality.sh --check
```
