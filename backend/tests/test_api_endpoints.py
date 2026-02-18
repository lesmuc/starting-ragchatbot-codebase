"""
API endpoint tests for /api/query and /api/courses.

Uses the `api_client` fixture from conftest.py, which spins up a minimal
FastAPI test app that mirrors app.py's endpoints without mounting static
files or initialising a real RAGSystem.
"""

import pytest


# ── POST /api/query ──────────────────────────────────────────────────────────

def test_query_returns_200_with_expected_shape(api_client):
    """Happy-path: 200 response contains answer, sources list, and session_id."""
    response = api_client.post("/api/query", json={"query": "What is Python?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert isinstance(data["sources"], list)
    assert "session_id" in data


def test_query_auto_creates_session_when_absent(api_client, mock_rag_system):
    """No session_id in request → session_manager.create_session() called once."""
    response = api_client.post("/api/query", json={"query": "What is Python?"})

    assert response.status_code == 200
    mock_rag_system.session_manager.create_session.assert_called_once()
    assert response.json()["session_id"] == "session_1"


def test_query_uses_provided_session_id(api_client, mock_rag_system):
    """Provided session_id is forwarded to rag.query() and echoed in response."""
    response = api_client.post(
        "/api/query",
        json={"query": "What is Python?", "session_id": "session_42"},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session_42"
    mock_rag_system.session_manager.create_session.assert_not_called()
    mock_rag_system.query.assert_called_once_with("What is Python?", "session_42")


def test_query_includes_sources_from_rag(api_client, mock_rag_system):
    """Sources returned by rag.query() appear verbatim in the JSON response."""
    mock_rag_system.query.return_value = (
        "Great answer",
        [{"text": "Python Fundamentals - Lesson 1", "url": "https://example.com/l1"}],
    )

    response = api_client.post("/api/query", json={"query": "Tell me about Python"})

    assert response.status_code == 200
    sources = response.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["text"] == "Python Fundamentals - Lesson 1"
    assert sources[0]["url"] == "https://example.com/l1"


def test_query_source_url_may_be_null(api_client, mock_rag_system):
    """Sources with no URL are accepted (url field is optional)."""
    mock_rag_system.query.return_value = (
        "Answer",
        [{"text": "Some content", "url": None}],
    )

    response = api_client.post("/api/query", json={"query": "test"})

    assert response.status_code == 200
    assert response.json()["sources"][0]["url"] is None


def test_query_missing_required_field_returns_422(api_client):
    """POST body without the required 'query' field → 422 Unprocessable Entity."""
    response = api_client.post("/api/query", json={"session_id": "session_1"})

    assert response.status_code == 422


def test_query_propagates_rag_error_as_500(api_client, mock_rag_system):
    """Exception raised by rag.query() → 500 with the error message in detail."""
    mock_rag_system.query.side_effect = RuntimeError("Upstream API failure")

    response = api_client.post("/api/query", json={"query": "What is Python?"})

    assert response.status_code == 500
    assert "Upstream API failure" in response.json()["detail"]


# ── GET /api/courses ─────────────────────────────────────────────────────────

def test_courses_returns_200_with_expected_shape(api_client):
    """Happy-path: 200 response contains total_courses and course_titles."""
    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 2
    assert data["course_titles"] == ["Python Fundamentals", "Advanced Python"]


def test_courses_empty_catalog(api_client, mock_rag_system):
    """Empty catalog → total_courses 0 and empty course_titles list."""
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }

    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 0
    assert data["course_titles"] == []


def test_courses_propagates_analytics_error_as_500(api_client, mock_rag_system):
    """Exception from get_course_analytics() → 500 with the error in detail."""
    mock_rag_system.get_course_analytics.side_effect = RuntimeError("Chroma unavailable")

    response = api_client.get("/api/courses")

    assert response.status_code == 500
    assert "Chroma unavailable" in response.json()["detail"]
