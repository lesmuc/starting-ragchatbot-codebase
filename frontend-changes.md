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

---

# Testing Framework Enhancements

## Changes Made

### `pyproject.toml`
- Added `httpx>=0.27` to dependencies (required by `starlette.testclient.TestClient`).
- Added `[tool.pytest.ini_options]` section:
  - `testpaths = ["backend/tests"]` — pytest discovers tests without needing `-p` flags or a manual path argument.
  - `pythonpath = ["backend"]` — backend modules (`app`, `rag_system`, etc.) are importable by pytest without manual `sys.path` manipulation.

### `backend/tests/conftest.py`
Added API test infrastructure alongside the existing vector-store fixtures:

- **`mock_rag_system` fixture** — a `Mock()` pre-wired with defaults for every method exercised by the API endpoints (`query`, `get_course_analytics`, `session_manager.create_session`). Function-scoped so each test gets a fresh mock.
- **`_build_test_app(rag)` helper** — constructs a minimal `FastAPI` instance that mirrors `app.py`'s `/api/query` and `/api/courses` endpoints but omits static-file mounting, avoiding the need for the `frontend/` directory to exist at test time.
- **`api_client` fixture** — wraps `_build_test_app(mock_rag_system)` in a `starlette.testclient.TestClient` for synchronous HTTP testing.

New imports added: `Mock`, `FastAPI`, `HTTPException`, `BaseModel`, `List`, `Optional`, `TestClient`.

### `backend/tests/test_api_endpoints.py` *(new file)*
10 tests covering the two API endpoints:

**`POST /api/query`**
| Test | What it verifies |
|---|---|
| `test_query_returns_200_with_expected_shape` | 200 + `answer`, `sources`, `session_id` keys present |
| `test_query_auto_creates_session_when_absent` | `session_manager.create_session()` called when no `session_id` in body |
| `test_query_uses_provided_session_id` | Provided `session_id` forwarded to `rag.query()` and echoed in response; `create_session` not called |
| `test_query_includes_sources_from_rag` | Source `text` and `url` pass through correctly |
| `test_query_source_url_may_be_null` | Optional `url` field accepts `null` |
| `test_query_missing_required_field_returns_422` | Body without `query` field → 422 |
| `test_query_propagates_rag_error_as_500` | Exception from `rag.query()` → 500 with error message in `detail` |

**`GET /api/courses`**
| Test | What it verifies |
|---|---|
| `test_courses_returns_200_with_expected_shape` | 200 + correct `total_courses` and `course_titles` |
| `test_courses_empty_catalog` | Zero courses → `total_courses: 0`, `course_titles: []` |
| `test_courses_propagates_analytics_error_as_500` | Exception from `get_course_analytics()` → 500 with error in `detail` |

## Design Decision: Inline Test App vs Importing `app.py`

`app.py` runs module-level code at import time — specifically `RAGSystem(config)` (requires Anthropic + ChromaDB) and `StaticFiles(directory="../frontend")` (requires the built frontend). Both would fail in CI or a clean checkout.

Rather than patching across multiple layers before import, a minimal test app is constructed inline in `conftest.py` using the same endpoint logic. This keeps the tests fast, dependency-free, and easy to maintain alongside the real app.
