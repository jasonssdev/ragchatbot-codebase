"""
API endpoint tests for the RAG chatbot FastAPI application.

Covers:
  POST /api/query  — query processing and session management
  GET  /api/courses — course catalog statistics
"""

import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_returns_answer_and_sources(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "What is RAG?"})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Test answer"
        assert body["sources"] == ["source1", "source2"]

    def test_creates_session_when_none_provided(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "Hello"})

        assert response.status_code == 200
        assert response.json()["session_id"] == "session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag_system):
        response = client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": "existing_session"},
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == "existing_session"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_passes_query_to_rag_system(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Explain transformers"})

        mock_rag_system.query.assert_called_once()
        call_args = mock_rag_system.query.call_args
        assert "Explain transformers" in call_args[0][0]

    def test_missing_query_field_returns_422(self, client, mock_rag_system):
        response = client.post("/api/query", json={"session_id": "abc"})

        assert response.status_code == 422

    def test_invalid_json_body_returns_422(self, client, mock_rag_system):
        response = client.post(
            "/api/query",
            content="not-json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_rag_exception_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("ChromaDB unavailable")

        response = client.post("/api/query", json={"query": "Crash me"})

        assert response.status_code == 500
        assert "ChromaDB unavailable" in response.json()["detail"]

    def test_response_schema_has_required_fields(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "Schema check"})

        body = response.json()
        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_sources_is_list(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "Sources type"})

        assert isinstance(response.json()["sources"], list)

    def test_empty_sources_list(self, client, mock_rag_system):
        mock_rag_system.query.return_value = ("No sources answer", [])

        response = client.post("/api/query", json={"query": "General question"})

        assert response.status_code == 200
        assert response.json()["sources"] == []


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_returns_course_stats(self, client, mock_rag_system):
        response = client.get("/api/courses")

        assert response.status_code == 200
        body = response.json()
        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Course A", "Course B"]

    def test_response_schema_has_required_fields(self, client, mock_rag_system):
        response = client.get("/api/courses")

        body = response.json()
        assert "total_courses" in body
        assert "course_titles" in body

    def test_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        body = response.json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []

    def test_course_titles_is_list(self, client, mock_rag_system):
        response = client.get("/api/courses")

        assert isinstance(response.json()["course_titles"], list)

    def test_total_courses_is_integer(self, client, mock_rag_system):
        response = client.get("/api/courses")

        assert isinstance(response.json()["total_courses"], int)

    def test_rag_exception_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "DB error" in response.json()["detail"]

    def test_calls_get_course_analytics(self, client, mock_rag_system):
        client.get("/api/courses")

        mock_rag_system.get_course_analytics.assert_called_once()
