import pytest
from unittest.mock import Mock, patch
from ai_generator import AIGenerator


def _make_text_response(text="Direct answer"):
    """Create a mock API response with stop_reason=end_turn"""
    mock_text_block = Mock()
    mock_text_block.type = "text"
    mock_text_block.text = text
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_text_block]
    return mock_response


def _make_tool_response(tool_name="search_course_content", tool_input=None):
    """Create a mock API response with stop_reason=tool_use"""
    if tool_input is None:
        tool_input = {"query": "test query"}
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = tool_name
    mock_tool_block.id = "tool_id_123"
    mock_tool_block.input = tool_input
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"
    mock_response.content = [mock_tool_block]
    return mock_response


@pytest.fixture
def mock_anthropic_client():
    """Yields a mock Anthropic client, patching the constructor"""
    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = Mock()
        MockAnthropic.return_value = mock_client
        yield mock_client


@pytest.fixture
def generator(mock_anthropic_client):
    """Returns an AIGenerator backed by the mock client"""
    return AIGenerator(api_key="test-key", model="claude-test-model")


def test_direct_answer_returned(mock_anthropic_client, generator):
    """stop_reason=end_turn → returns content[0].text"""
    mock_anthropic_client.messages.create.return_value = _make_text_response(
        "Direct answer"
    )

    result = generator.generate_response(query="What is Python?")

    assert result == "Direct answer"


def test_tool_use_triggers_tool_manager(mock_anthropic_client, generator):
    """stop_reason=tool_use → tool_manager.execute_tool() is called"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_text_response("Final answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Search results"

    generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    mock_tool_manager.execute_tool.assert_called_once()


def test_tool_name_and_args_correct(mock_anthropic_client, generator):
    """execute_tool called with 'search_course_content' and the right kwargs"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(
            tool_name="search_course_content",
            tool_input={"query": "python basics", "course_name": "Python"},
        ),
        _make_text_response("Final answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Results"

    generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    mock_tool_manager.execute_tool.assert_called_once_with(
        "search_course_content",
        query="python basics",
        course_name="Python",
    )


def test_tool_result_sent_to_claude(mock_anthropic_client, generator):
    """Second API call includes a tool_result message"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_text_response("Final answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Search results"

    generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    tool_result_found = any(
        isinstance(msg.get("content"), list)
        and any(
            isinstance(item, dict) and item.get("type") == "tool_result"
            for item in msg.get("content", [])
        )
        for msg in messages
    )
    assert tool_result_found


def test_tools_param_passed_to_api(mock_anthropic_client, generator):
    """tools and tool_choice=auto present in first API call"""
    mock_anthropic_client.messages.create.return_value = _make_text_response()
    tools = [{"name": "search_course_content"}]

    generator.generate_response(query="What is Python?", tools=tools)

    first_call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "tools" in first_call_kwargs
    assert first_call_kwargs["tool_choice"] == {"type": "auto"}


def test_no_tools_in_final_api_call(mock_anthropic_client, generator):
    """After rounds exhausted, synthesis call has no tools"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),          # round 0: tool_use
        _make_tool_response(),          # round 1: tool_use → rounds exhausted
        _make_text_response("Synthesis"),  # final no-tools call
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Results"

    result = generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    assert result == "Synthesis"
    assert mock_anthropic_client.messages.create.call_count == 3
    final_kwargs = mock_anthropic_client.messages.create.call_args_list[-1][1]
    assert "tools" not in final_kwargs


def test_two_round_chaining(mock_anthropic_client, generator):
    """[tool, tool, end_turn]: 3 API calls, execute_tool called twice, correct final text"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_tool_response(),
        _make_text_response("Chained answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Results"

    result = generator.generate_response(
        query="Multi-step query",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    assert result == "Chained answer"
    assert mock_anthropic_client.messages.create.call_count == 3
    assert mock_tool_manager.execute_tool.call_count == 2


def test_end_turn_after_one_round_no_extra_call(mock_anthropic_client, generator):
    """[tool, end_turn]: 2 API calls, text returned directly, no synthesis call"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_text_response("One-round answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Results"

    result = generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    assert result == "One-round answer"
    assert mock_anthropic_client.messages.create.call_count == 2


def test_tool_execution_error_handled_gracefully(mock_anthropic_client, generator):
    """execute_tool raises → error string in tool_result → method returns a string"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_text_response("Graceful answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = RuntimeError("DB connection failed")

    result = generator.generate_response(
        query="What is Python?",
        tools=[{"name": "search_course_content"}],
        tool_manager=mock_tool_manager,
    )

    assert isinstance(result, str)
    # The error message should be passed to Claude as tool_result content
    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]
    tool_result_content = next(
        item["content"]
        for msg in messages
        if isinstance(msg.get("content"), list)
        for item in msg["content"]
        if isinstance(item, dict) and item.get("type") == "tool_result"
    )
    assert "Tool execution error" in tool_result_content


def test_intermediate_rounds_include_tools(mock_anthropic_client, generator):
    """Call at index 1 (first loop re-call) still has tools + tool_choice in kwargs"""
    mock_anthropic_client.messages.create.side_effect = [
        _make_tool_response(),
        _make_text_response("Answer"),
    ]
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Results"
    tools = [{"name": "search_course_content"}]

    generator.generate_response(
        query="What is Python?",
        tools=tools,
        tool_manager=mock_tool_manager,
    )

    second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
    assert "tools" in second_call_kwargs
    assert second_call_kwargs["tool_choice"] == {"type": "auto"}
