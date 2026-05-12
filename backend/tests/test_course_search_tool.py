from unittest.mock import MagicMock, call
import pytest

from vector_store import SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool


# ── 1.1 Happy path ────────────────────────────────────────────────────────────

def test_execute_returns_formatted_result(mock_vector_store, sample_search_results):
    mock_vector_store.search.return_value = sample_search_results
    mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson3"
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="What is Python?")

    assert "[Intro to Python - Lesson 3]" in result
    assert "Python is a high-level language." in result
    mock_vector_store.search.assert_called_once_with(
        query="What is Python?", course_name=None, lesson_number=None
    )


# ── 1.2 course_name filter forwarded ─────────────────────────────────────────

def test_execute_forwards_course_name_filter(mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content..."],
        metadata=[{"course_title": "MCP Course", "lesson_number": None}],
        distances=[0.1],
    )
    tool = CourseSearchTool(mock_vector_store)

    tool.execute(query="What is MCP?", course_name="MCP")

    mock_vector_store.search.assert_called_once_with(
        query="What is MCP?", course_name="MCP", lesson_number=None
    )


# ── 1.3 Empty results, no filters ────────────────────────────────────────────

def test_execute_empty_results_no_filter(mock_vector_store, empty_search_results):
    mock_vector_store.search.return_value = empty_search_results
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="quantum computing")

    assert result == "No relevant content found."
    mock_vector_store.get_lesson_link.assert_not_called()


# ── 1.4 Empty results with course_name ───────────────────────────────────────

def test_execute_empty_results_with_course_name(mock_vector_store, empty_search_results):
    mock_vector_store.search.return_value = empty_search_results
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="XYZ", course_name="Advanced Python")

    assert "in course 'Advanced Python'" in result
    assert result.startswith("No relevant content found")


# ── 1.5 Empty results with lesson_number=0  [EXPECTS TO FAIL — Bug B1] ───────

def test_execute_empty_results_with_lesson_number_zero(mock_vector_store, empty_search_results):
    mock_vector_store.search.return_value = empty_search_results
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="intro", lesson_number=0)

    # Bug B1: `if lesson_number:` is falsy for 0 — "in lesson 0" will NOT appear
    assert "in lesson 0" in result


# ── 1.6 Error propagation ─────────────────────────────────────────────────────

def test_execute_returns_error_string(mock_vector_store, error_search_results):
    mock_vector_store.search.return_value = error_search_results
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="anything")

    assert result == "DB timeout"
    assert tool.last_sources == []
    mock_vector_store.get_lesson_link.assert_not_called()


# ── 1.7 last_sources populated correctly ─────────────────────────────────────

def test_execute_populates_last_sources(mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Doc A", "Doc B"],
        metadata=[
            {"course_title": "Course A", "lesson_number": 2},
            {"course_title": "Course B", "lesson_number": None},
        ],
        distances=[0.1, 0.3],
    )
    mock_vector_store.get_lesson_link.return_value = "https://a.com/lesson2"
    tool = CourseSearchTool(mock_vector_store)

    tool.execute(query="test")

    assert len(tool.last_sources) == 2
    assert tool.last_sources[0] == {"label": "Course A - Lesson 2", "url": "https://a.com/lesson2"}
    assert tool.last_sources[1] == {"label": "Course B", "url": None}
    mock_vector_store.get_lesson_link.assert_called_once_with("Course A", 2)


# ── 1.8 last_sources replaced on second call ─────────────────────────────────

def test_execute_replaces_last_sources_on_second_call(mock_vector_store):
    two_results = SearchResults(
        documents=["A", "B"],
        metadata=[
            {"course_title": "C", "lesson_number": 1},
            {"course_title": "C", "lesson_number": 2},
        ],
        distances=[0.1, 0.2],
    )
    one_result = SearchResults(
        documents=["X"],
        metadata=[{"course_title": "D", "lesson_number": None}],
        distances=[0.1],
    )
    mock_vector_store.search.side_effect = [two_results, one_result]
    tool = CourseSearchTool(mock_vector_store)

    tool.execute(query="first")
    assert len(tool.last_sources) == 2

    tool.execute(query="second")
    assert len(tool.last_sources) == 1


# ── 1.9 get_lesson_link not called when lesson_num is None ───────────────────

def test_execute_skips_lesson_link_when_lesson_num_is_none(mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["Content"],
        metadata=[{"course_title": "Python Basics", "lesson_number": None}],
        distances=[0.2],
    )
    tool = CourseSearchTool(mock_vector_store)

    tool.execute(query="test")

    mock_vector_store.get_lesson_link.assert_not_called()


# ── 1.10 Multi-result output separated by double newline ─────────────────────

def test_execute_separates_multiple_results_with_double_newline(mock_vector_store):
    mock_vector_store.search.return_value = SearchResults(
        documents=["A", "B", "C"],
        metadata=[
            {"course_title": "X", "lesson_number": None},
            {"course_title": "X", "lesson_number": None},
            {"course_title": "X", "lesson_number": None},
        ],
        distances=[0.1, 0.2, 0.3],
    )
    tool = CourseSearchTool(mock_vector_store)

    result = tool.execute(query="test")

    assert result.count("\n\n") == 2


# ── 1.11 CourseOutlineTool happy path ────────────────────────────────────────

def test_outline_tool_returns_formatted_outline(mock_vector_store):
    mock_vector_store.get_course_outline.return_value = {
        "title": "Intro to Python",
        "course_link": "https://example.com",
        "lessons": [
            {"lesson_number": 1, "lesson_title": "Variables"},
            {"lesson_number": 2, "lesson_title": "Functions"},
        ],
    }
    from search_tools import CourseOutlineTool
    tool = CourseOutlineTool(mock_vector_store)

    result = tool.execute(course_name="Python")

    assert "Course: Intro to Python" in result
    assert "Link: https://example.com" in result
    assert "Lesson 1: Variables" in result
    assert "Lesson 2: Functions" in result


# ── 1.12 CourseOutlineTool not-found ─────────────────────────────────────────

def test_outline_tool_returns_not_found_message(mock_vector_store):
    mock_vector_store.get_course_outline.return_value = None
    from search_tools import CourseOutlineTool
    tool = CourseOutlineTool(mock_vector_store)

    result = tool.execute(course_name="Nonexistent")

    assert result == "No course found matching 'Nonexistent'."


# ── 1.13 CourseOutlineTool has no last_sources attribute ─────────────────────

def test_outline_tool_has_no_last_sources(mock_vector_store):
    from search_tools import CourseOutlineTool
    tool = CourseOutlineTool(mock_vector_store)
    assert not hasattr(tool, "last_sources")
