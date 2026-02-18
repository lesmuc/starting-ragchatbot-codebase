import pytest
from search_tools import CourseSearchTool
from vector_store import SearchResults


def test_formatted_results_returned(mock_vector_store, sample_search_results):
    """Output contains course title, lesson header, and doc text"""
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="python basics")

    assert "Python Fundamentals" in result
    assert "Lesson 1" in result
    assert "This is lesson content about Python basics." in result


def test_no_results_message(mock_vector_store):
    """Empty SearchResults → 'No relevant content found'"""
    mock_vector_store.search.return_value = SearchResults(
        documents=[], metadata=[], distances=[]
    )
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="nonexistent topic")

    assert "No relevant content found" in result


def test_error_message_propagated(mock_vector_store):
    """SearchResults.error set → error string returned"""
    mock_vector_store.search.return_value = SearchResults.empty(
        "Search error: connection failed"
    )
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="test")

    assert "Search error: connection failed" in result


def test_course_name_forwarded(mock_vector_store):
    """store.search() called with correct course_name"""
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="python basics", course_name="Python Fundamentals")

    mock_vector_store.search.assert_called_once_with(
        query="python basics",
        course_name="Python Fundamentals",
        lesson_number=None,
    )


def test_lesson_number_forwarded(mock_vector_store):
    """store.search() called with correct lesson_number"""
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="python basics", lesson_number=3)

    mock_vector_store.search.assert_called_once_with(
        query="python basics",
        course_name=None,
        lesson_number=3,
    )


def test_sources_tracked(mock_vector_store):
    """last_sources populated with text and url after search"""
    tool = CourseSearchTool(mock_vector_store)
    tool.execute(query="python basics")

    assert len(tool.last_sources) == 1
    assert tool.last_sources[0]["text"] == "Python Fundamentals - Lesson 1"
    assert tool.last_sources[0]["url"] == "https://example.com/lesson1"


def test_no_results_with_course_name_in_message(mock_vector_store):
    """Filter info appears in 'no results' message"""
    mock_vector_store.search.return_value = SearchResults(
        documents=[], metadata=[], distances=[]
    )
    tool = CourseSearchTool(mock_vector_store)
    result = tool.execute(query="test", course_name="Python Fundamentals")

    assert "No relevant content found" in result
    assert "Python Fundamentals" in result
