import sys
import os
import pytest
from unittest.mock import MagicMock

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
