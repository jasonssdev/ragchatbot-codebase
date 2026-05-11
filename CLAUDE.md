# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Install dependencies (first time)
uv sync

# Set up environment
cp .env.example .env   # then add your ANTHROPIC_API_KEY

# Start the server
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000`, API docs at `http://localhost:8000/docs`.

Always use `uv` for all dependency management and running the server — never use `pip` directly.

```bash
uv add <package>        # add a dependency
uv remove <package>     # remove a dependency
uv sync                 # install all dependencies from lockfile
uv run <script>.py      # run a Python file
uv run python           # start a Python REPL
```

All backend modules must be run from the `backend/` directory — imports are relative (e.g., `from config import config`), not package-qualified.

## Architecture

This is a full-stack RAG chatbot: a vanilla JS frontend served as static files by the same FastAPI server that exposes the API.

### Query pipeline (the core flow)

```text
User query (JS fetch POST /api/query)
  → app.py: creates/looks up session, calls rag_system.query()
  → rag_system.py: fetches conversation history, calls ai_generator.generate_response()
  → ai_generator.py: Claude API Call 1 (with search tool available)
      └─ if Claude decides to search:
           → search_tools.py CourseSearchTool.execute()
           → vector_store.py VectorStore.search()
               ├─ _resolve_course_name(): semantic match in course_catalog collection
               └─ course_content.query(): embedding similarity search
           → Claude API Call 2 (tool results fed back, no tools this round)
  → rag_system.py: collects sources, persists exchange to SessionManager
  → response JSON { answer, sources, session_id } back to frontend
```

Claude decides whether to call the search tool — general knowledge questions skip retrieval entirely.

### Key files

| File | Role |
| --- | --- |
| `backend/app.py` | FastAPI app, two endpoints: `POST /api/query`, `GET /api/courses` |
| `backend/rag_system.py` | Orchestrator — wires all components together |
| `backend/ai_generator.py` | Anthropic SDK calls; handles the two-turn tool-use loop |
| `backend/search_tools.py` | `CourseSearchTool` + `ToolManager`; tool definition sent to Claude |
| `backend/vector_store.py` | ChromaDB wrapper; two collections: `course_catalog`, `course_content` |
| `backend/document_processor.py` | Parses course `.txt` files into `Course`/`Lesson`/`CourseChunk` models |
| `backend/session_manager.py` | In-memory conversation history, capped at `MAX_HISTORY` exchanges |
| `backend/config.py` | Single `Config` dataclass; all tunables live here |
| `backend/models.py` | Pydantic models: `Course`, `Lesson`, `CourseChunk` |
| `frontend/script.js` | All UI logic; calls `/api/query` and `/api/courses` |

### Document format

Course files in `docs/` must follow this structure for `DocumentProcessor` to parse them correctly:

```text
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <title>
Lesson Link: <url>
<lesson content...>

Lesson 2: <title>
...
```

The `course_title` is used as the ChromaDB document ID — it must be unique across all loaded courses.

### ChromaDB collections

- **`course_catalog`** — one document per course (title text), used for fuzzy course name resolution
- **`course_content`** — one document per chunk (800 chars, 100 overlap), filtered by `course_title` and `lesson_number` metadata

The vector store persists to `backend/chroma_db/`. Documents are not re-indexed on restart if their course title already exists in the catalog.

### Configuration knobs (`backend/config.py`)

| Key | Default | Effect |
| --- | --- | --- |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model for embeddings |
| `CHUNK_SIZE` | `800` | Max characters per content chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks |
| `MAX_RESULTS` | `5` | ChromaDB results returned per search |
| `MAX_HISTORY` | `2` | Conversation turns kept in session context |
