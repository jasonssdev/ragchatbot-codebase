# Changes — Testing Framework Enhancement

Note: these are backend testing changes, not frontend changes. The feature request
asked for API endpoint tests covering the FastAPI app that serves the frontend.

## Files created

### `backend/tests/__init__.py`
Empty package marker so pytest treats the directory as a package.

### `backend/tests/conftest.py`
Shared test infrastructure:
- Injects a fake `rag_system` module into `sys.modules` before `app.py` is
  imported, so `RAGSystem()` is never constructed (no ChromaDB / model init).
- Patches `StaticFiles.__init__` to a no-op so the `../frontend` mount in
  `app.py` does not raise `RuntimeError` when the frontend directory is absent.
- `mock_rag_system` fixture — returns the shared `MagicMock` reset to safe
  defaults (including explicit `side_effect = None`) before every test.
- `client` fixture — `TestClient` wrapping the real `app` from `app.py`,
  depends on `mock_rag_system` so mocks are always fresh.

### `backend/tests/test_api.py`
17 tests across two classes:

**`TestQueryEndpoint` (POST /api/query)**
- Returns correct answer and sources
- Creates a new session when none is provided
- Uses an existing session_id when supplied
- Passes the query string through to RAGSystem
- Returns 422 for missing `query` field
- Returns 422 for invalid JSON body
- Returns 500 with error detail when RAGSystem raises
- Response schema contains `answer`, `sources`, `session_id`
- `sources` field is a list
- Handles empty sources list

**`TestCoursesEndpoint` (GET /api/courses)**
- Returns `total_courses` and `course_titles`
- Response schema contains required fields
- Handles empty catalog (0 courses, empty list)
- `course_titles` is a list
- `total_courses` is an integer
- Returns 500 with error detail when RAGSystem raises
- Calls `get_course_analytics` exactly once

## Files modified

### `pyproject.toml`
Added:
- `[dependency-groups] dev` with `pytest`, `httpx`, and `pytest-mock`
- `[tool.pytest.ini_options]` with `testpaths`, `pythonpath`, and `addopts`

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["backend"]
addopts = "-v --tb=short"
```

## Running the tests

```bash
uv run pytest
```
