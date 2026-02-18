import sys
import os
import pytest
from unittest.mock import MagicMock, Mock
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from starlette.testclient import TestClient

# Add the backend directory to sys.path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import VectorStore, SearchResults


@pytest.fixture
def sample_search_results():
    """A populated SearchResults with one document"""
    return SearchResults(
        documents=["This is lesson content about Python basics."],
        metadata=[{"course_title": "Python Fundamentals", "lesson_number": 1}],
        distances=[0.15],
    )


@pytest.fixture
def mock_vector_store(sample_search_results):
    """MagicMock of VectorStore with pre-wired search() and get_lesson_link()"""
    mock_store = MagicMock(spec=VectorStore)
    mock_store.search.return_value = sample_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson1"
    return mock_store


# ---------------------------------------------------------------------------
# API test infrastructure
# ---------------------------------------------------------------------------

# Pydantic models mirroring app.py (defined once at module level)
class _QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class _Source(BaseModel):
    text: str
    url: Optional[str] = None


class _QueryResponse(BaseModel):
    answer: str
    sources: List[_Source]
    session_id: str


class _CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def _build_test_app(rag) -> FastAPI:
    """Return a minimal FastAPI app wired to *rag* that mirrors app.py endpoints.

    Static-file mounting is intentionally omitted so the test app works
    without the frontend directory present.
    """
    app = FastAPI()

    @app.post("/api/query", response_model=_QueryResponse)
    async def query_documents(request: _QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return _QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=_CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return _CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem with sane defaults for all endpoint-exercised methods."""
    mock = Mock()
    mock.query.return_value = ("Test answer", [])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Fundamentals", "Advanced Python"],
    }
    mock.session_manager.create_session.return_value = "session_1"
    return mock


@pytest.fixture
def api_client(mock_rag_system):
    """TestClient backed by a minimal test app wired to mock_rag_system."""
    return TestClient(_build_test_app(mock_rag_system))
