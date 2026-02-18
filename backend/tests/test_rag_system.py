import pytest
from unittest.mock import Mock, patch
from rag_system import RAGSystem


@pytest.fixture
def rag_system():
    """RAGSystem with all heavy dependencies patched out"""
    with patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator"), \
         patch("rag_system.SessionManager"), \
         patch("rag_system.DocumentProcessor"), \
         patch("rag_system.ToolManager"), \
         patch("rag_system.CourseSearchTool"), \
         patch("rag_system.CourseOutlineTool"):

        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test_chroma"
        config.EMBEDDING_MODEL = "test-model"
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test"
        config.MAX_HISTORY = 2

        system = RAGSystem(config)

        # Replace auto-mocked attributes with controlled mocks
        system.ai_generator = Mock()
        system.tool_manager = Mock()
        system.session_manager = Mock()

        # Wire up sane defaults
        system.ai_generator.generate_response.return_value = "Test answer"
        system.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content"}
        ]
        system.tool_manager.get_last_sources.return_value = []
        system.session_manager.get_conversation_history.return_value = None

        yield system


def test_query_returns_answer_and_sources(rag_system):
    """query() returns a (str, list) tuple"""
    result = rag_system.query("What is Python?")

    assert isinstance(result, tuple)
    assert len(result) == 2
    answer, sources = result
    assert isinstance(answer, str)
    assert isinstance(sources, list)


def test_tools_passed_to_generator(rag_system):
    """generate_response called with the 'tools' kwarg"""
    rag_system.query("What is Python?")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert "tools" in call_kwargs
    assert call_kwargs["tools"] == [{"name": "search_course_content"}]


def test_tool_manager_passed_to_generator(rag_system):
    """generate_response called with the 'tool_manager' kwarg"""
    rag_system.query("What is Python?")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert "tool_manager" in call_kwargs
    assert call_kwargs["tool_manager"] is rag_system.tool_manager


def test_sources_reset_after_query(rag_system):
    """tool_manager.reset_sources() called after every query"""
    rag_system.query("What is Python?")

    rag_system.tool_manager.reset_sources.assert_called_once()


def test_session_history_passed(rag_system):
    """Prior conversation history appears in conversation_history kwarg"""
    history_text = "User: hello\nAssistant: hi there"
    rag_system.session_manager.get_conversation_history.return_value = history_text

    rag_system.query("What is Python?", session_id="session_1")

    call_kwargs = rag_system.ai_generator.generate_response.call_args[1]
    assert call_kwargs["conversation_history"] == history_text


def test_exception_propagates(rag_system):
    """Exception from generate_response bubbles up (causes HTTP 500)"""
    rag_system.ai_generator.generate_response.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        rag_system.query("What is Python?")
