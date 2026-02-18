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

---

# Frontend Changes

## Feature: Dark / Light Theme Toggle

### Files Modified

#### `frontend/index.html`
- **FOUC prevention**: Added an inline `<script>` in `<head>` that reads `localStorage.getItem('theme')` and immediately sets `data-theme` on `<html>` before any paint, eliminating flash-of-unstyled-content when the saved theme is light.
- **Toggle button**: Added a fixed-position `<button id="themeToggle" class="theme-toggle">` just before `</body>`. Contains two inline SVGs — `.icon-sun` (visible in dark mode) and `.icon-moon` (visible in light mode) — both present in the DOM at all times so CSS transitions can animate between them.
- **Cache-buster versions**: bumped `style.css?v=10` → `v=11` and `script.js?v=9` → `v=10`.

#### `frontend/style.css`
Four new sections appended after the existing responsive breakpoints:

1. **Light theme variables** (`[data-theme="light"]`)
   Overrides every `:root` CSS custom property with light-appropriate values:
   - `--background: #f1f5f9` — light slate-gray page background
   - `--surface: #ffffff` — white card/sidebar surface
   - `--surface-hover: #e2e8f0`
   - `--text-primary: #0f172a` — near-black for strong contrast
   - `--text-secondary: #64748b`
   - `--border-color: #cbd5e1`
   - `--shadow`, `--focus-ring`, `--welcome-bg`, `--welcome-border` adjusted for light context

2. **Smooth theme transitions**
   Targeted `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` added to `body`, `.sidebar`, `.chat-main`, `.chat-container`, `.chat-messages`, `.chat-input-container`, `.message-content`, `.stat-item`, `.course-title-item`. Elements that already have `transition: all` (e.g. `#chatInput`, `.suggested-item`) are intentionally excluded to avoid overriding their existing hover/focus animations.

3. **Theme toggle button styles** (`.theme-toggle`)
   - `position: fixed; top: 1rem; right: 1rem` — top-right corner, always visible
   - 40 × 40 px circle with `border-radius: 50%`
   - Uses `--surface`, `--border-color`, `--text-secondary` CSS variables so it automatically adapts to both themes
   - Hover: scale 1.08, primary-color border/icon tint
   - Focus: `box-shadow: 0 0 0 3px var(--focus-ring)` for keyboard accessibility
   - Active: scale 0.9 for tactile feedback
   - Both SVG icons use `position: absolute` + `opacity` + `transform: rotate()` transitions to create a smooth crossfade-with-rotation swap on theme change:
     - Dark mode → sun fades in at 0°, moon fades out at 90°
     - Light mode → moon fades in at 0°, sun fades out at −90°

4. **Light theme specific overrides**
   - `.sources-content a`: blue pill links re-colored for a light background
   - `.sources-content span`: muted pill adjusted
   - `.message-content code` / `pre`: `rgba(0,0,0,0.06)` tint instead of the darker dark-mode value

#### `frontend/script.js`
- **`initTheme()`**: Called on `DOMContentLoaded`; reads the `data-theme` already set by the inline head script and syncs the toggle button's `aria-label`.
- **`toggleTheme()`**: Reads current `data-theme` from `document.documentElement`, flips it between `'dark'` and `'light'`, writes back to the element and to `localStorage`, then calls `updateToggleLabel()`.
- **`updateToggleLabel(theme)`**: Keeps the button's `aria-label` accurate (`"Switch to light theme"` / `"Switch to dark theme"`).
- **`setupEventListeners()`**: Wired `click` on `#themeToggle` to `toggleTheme()`.
- **`DOMContentLoaded` handler**: Added `initTheme()` call after `setupEventListeners()`.

### Design Decisions
- **`data-theme` on `<html>`** (not `<body>`) so the inline head script can set it before the body renders, preventing any flicker.
- **Dual SVG / opacity approach** instead of `display:none/block` so CSS transitions can animate the icon swap.
- **`localStorage` persistence** — the chosen theme survives page refresh and future visits.
- **Dark as default** — matches the existing stylesheet's `:root` variables; no additional selector needed for dark mode.
- **No `transition: all` override** — existing hover/interactive animations are preserved by only adding transitions to elements that didn't already have them.
