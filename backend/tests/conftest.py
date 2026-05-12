"""
Shared fixtures for the RAG system test suite.

Strategy for handling app.py's module-level side effects:
 - rag_system module is injected into sys.modules before app is imported,
   so RAGSystem() is never actually constructed (no ChromaDB / model loading).
 - StaticFiles.__init__ is patched to a no-op so the ../frontend mount does
   not raise RuntimeError when that directory is absent in the test tree.

Both patches are started at module-level so they are in place before pytest
collects and imports any test file that references `app`.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# sys.path: let imports like `from config import config` resolve from backend/
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Shared RAGSystem mock instance (bound to app.py's module-level `rag_system`)
# ---------------------------------------------------------------------------
_rag_mock = MagicMock()
_rag_mock.session_manager.create_session.return_value = "session_1"
_rag_mock.query.return_value = ("Test answer", ["source1", "source2"])
_rag_mock.get_course_analytics.return_value = {
    "total_courses": 2,
    "course_titles": ["Course A", "Course B"],
}
_rag_mock.add_course_folder.return_value = (0, 0)

# Inject a fake rag_system module so `from rag_system import RAGSystem` in
# app.py receives our mock class instead of the real one.
_rag_module = MagicMock()
_rag_module.RAGSystem = MagicMock(return_value=_rag_mock)
sys.modules["rag_system"] = _rag_module

# Patch StaticFiles.__init__ to skip the directory-existence check.
_static_patcher = patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None)
_static_patcher.start()

# Safe to import the real app now.
from app import app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """Return the shared RAGSystem mock, reset to defaults before each test."""
    _rag_mock.reset_mock()
    _rag_mock.session_manager.reset_mock()
    # Explicitly clear side_effects — reset_mock() does not do this by default.
    _rag_mock.query.side_effect = None
    _rag_mock.get_course_analytics.side_effect = None
    _rag_mock.add_course_folder.side_effect = None
    _rag_mock.session_manager.create_session.side_effect = None
    # Restore default return values.
    _rag_mock.session_manager.create_session.return_value = "session_1"
    _rag_mock.query.return_value = ("Test answer", ["source1", "source2"])
    _rag_mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    _rag_mock.add_course_folder.return_value = (0, 0)
    return _rag_mock


@pytest.fixture
def client(mock_rag_system):
    """TestClient wrapping the real FastAPI app with a fresh mock each test."""
    return TestClient(app, raise_server_exceptions=True)
