from unittest.mock import MagicMock, patch
import pytest

from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from rag_system import RAGSystem


@pytest.fixture
def rag_system(mocker):
    mocker.patch("rag_system.VectorStore")
    mocker.patch("rag_system.DocumentProcessor")
    mocker.patch("rag_system.AIGenerator")
    mocker.patch("rag_system.SessionManager")

    config = MagicMock()
    config.ANTHROPIC_API_KEY = "fake-key"
    config.ANTHROPIC_MODEL = "claude-test"
    config.CHROMA_PATH = "/tmp/test_chroma"
    config.EMBEDDING_MODEL = "test-model"
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100

    system = RAGSystem(config)
    system.ai_generator.generate_response.return_value = "Mocked AI response."
    system.session_manager.get_conversation_history.return_value = None
    return system


# ── 3.1 Prompt is wrapped before being sent to AI ────────────────────────────

def test_query_wraps_prompt(rag_system):
    rag_system.query("What is Python?")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert call_kwargs["query"] == "Answer this question about course materials: What is Python?"


# ── 3.2 Both tools included in AI call ───────────────────────────────────────

def test_query_passes_both_tool_definitions_to_ai(rag_system):
    rag_system.query("test question")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    tool_names = [t["name"] for t in call_kwargs["tools"]]
    assert "search_course_content" in tool_names
    assert "get_course_outline" in tool_names


# ── 3.3 Sources from search_tool returned from query() ───────────────────────

def test_query_returns_sources_from_search_tool(rag_system):
    rag_system.search_tool.last_sources = [{"label": "Course A - Lesson 1", "url": "https://a.com"}]

    response, sources = rag_system.query("What is RAG?")

    assert sources == [{"label": "Course A - Lesson 1", "url": "https://a.com"}]


# ── 3.4 Sources are reset after query() ──────────────────────────────────────

def test_query_resets_sources_after_retrieval(rag_system):
    rag_system.search_tool.last_sources = [{"label": "Course A", "url": None}]

    rag_system.query("What is RAG?")

    assert rag_system.search_tool.last_sources == []


# ── 3.5 No session_id → session methods not called ───────────────────────────

def test_query_without_session_id_skips_session_ops(rag_system):
    rag_system.query("What is Python?")

    rag_system.session_manager.get_conversation_history.assert_not_called()
    rag_system.session_manager.add_exchange.assert_not_called()


# ── 3.6 With session_id → history fetched and forwarded to AI ────────────────

def test_query_with_session_id_fetches_and_forwards_history(rag_system):
    rag_system.session_manager.get_conversation_history.return_value = "User: Hi\nAssistant: Hello"

    rag_system.query("Tell me more", session_id="session_1")

    rag_system.session_manager.get_conversation_history.assert_called_once_with("session_1")
    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] == "User: Hi\nAssistant: Hello"


# ── 3.7 add_exchange receives raw query, not wrapped prompt ──────────────────

def test_query_stores_raw_query_in_session(rag_system):
    rag_system.ai_generator.generate_response.return_value = "RAG uses retrieval."

    rag_system.query("What is RAG?", session_id="session_1")

    rag_system.session_manager.add_exchange.assert_called_once_with(
        "session_1",
        "What is RAG?",
        "RAG uses retrieval.",
    )


# ── 3.8 None history forwarded as None, not empty string ─────────────────────

def test_query_forwards_none_history_not_empty_string(rag_system):
    rag_system.session_manager.get_conversation_history.return_value = None

    rag_system.query("First question", session_id="session_new")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] is None


# ── 3.9 query() returns (str, list) tuple ────────────────────────────────────

def test_query_returns_str_list_tuple(rag_system):
    result = rag_system.query("test")

    assert isinstance(result, tuple)
    assert len(result) == 2
    response, sources = result
    assert isinstance(response, str)
    assert isinstance(sources, list)


# ── 3.10 Empty sources when no search ran ────────────────────────────────────

def test_query_returns_empty_sources_when_no_search_ran(rag_system):
    rag_system.search_tool.last_sources = []

    response, sources = rag_system.query("Give me an outline")

    assert sources == []


# ── 3.11 ToolManager.get_last_sources returns first tool's sources ────────────

def test_tool_manager_get_last_sources_returns_first_match():
    manager = ToolManager()

    tool_a = MagicMock()
    tool_a.get_tool_definition.return_value = {"name": "tool_a"}
    tool_a.last_sources = [{"label": "A", "url": None}]

    tool_b = MagicMock()
    tool_b.get_tool_definition.return_value = {"name": "tool_b"}
    tool_b.last_sources = [{"label": "B", "url": None}]

    manager.register_tool(tool_a)
    manager.register_tool(tool_b)

    sources = manager.get_last_sources()

    assert sources == [{"label": "A", "url": None}]


# ── 3.12 reset_sources does not crash on tools without last_sources ───────────

def test_tool_manager_reset_sources_skips_tools_without_last_sources():
    manager = ToolManager()

    search_tool = MagicMock()
    search_tool.get_tool_definition.return_value = {"name": "search_course_content"}
    search_tool.last_sources = [{"label": "X", "url": None}]

    outline_tool = MagicMock(spec=["get_tool_definition", "execute"])
    outline_tool.get_tool_definition.return_value = {"name": "get_course_outline"}

    manager.register_tool(search_tool)
    manager.register_tool(outline_tool)

    manager.reset_sources()

    assert search_tool.last_sources == []
    assert not hasattr(outline_tool, "last_sources")
