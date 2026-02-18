# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

Requires a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_key_here
```

App is served at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

## Architecture

Full-stack RAG chatbot. FastAPI backend serves the frontend as static files and exposes two endpoints: `POST /api/query` and `GET /api/courses`.

**Query pipeline** (one user message triggers up to two Claude API calls):
1. `app.py` receives the request, delegates to `RAGSystem.query()`
2. `RAGSystem` passes the query + conversation history to `AIGenerator`
3. Claude decides whether to call the `search_course_content` tool (for course-specific questions) or answer directly (general knowledge)
4. If tool use: `CourseSearchTool` runs a semantic search against ChromaDB and returns formatted chunks back to Claude
5. Claude produces a final answer; sources and session history are updated

**Vector store** (`vector_store.py`) maintains two ChromaDB collections:
- `course_catalog` — one document per course (title, instructor, links, lesson list as JSON)
- `course_content` — chunked lesson text, filtered by `course_title` and/or `lesson_number`

Course name resolution is fuzzy: a semantic search against `course_catalog` maps partial names to exact titles before filtering `course_content`.

**Session history** is stored in-memory only (lost on server restart), keyed by `session_N` IDs. History is injected into the system prompt, not as message turns.

## Key Configuration (`backend/config.py`)

| Setting | Default |
|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | 800 chars |
| `CHUNK_OVERLAP` | 100 chars |
| `MAX_RESULTS` | 5 search results |
| `MAX_HISTORY` | 2 conversation exchanges |
| `CHROMA_PATH` | `./chroma_db` (relative to `backend/`) |

## Course Document Format

Files in `docs/` must follow this structure (`.txt`, `.pdf`, or `.docx`):
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>
Lesson 1: <lesson title>
Lesson Link: <url>
<lesson content...>
Lesson 2: <lesson title>
...
```

On startup, `app.py` loads all docs from `../docs` (relative to `backend/`), skipping courses already in ChromaDB. To force a reload, call `add_course_folder(..., clear_existing=True)`.

## Adding New Tools

Tools follow a simple pattern in `search_tools.py`: subclass `Tool`, implement `get_tool_definition()` (returns an Anthropic tool schema) and `execute(**kwargs)`, then register with `ToolManager`. The tool manager handles dispatch and Claude's tool-use loop is in `AIGenerator._handle_tool_execution()`.
