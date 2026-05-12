from unittest.mock import MagicMock, patch, call
import pytest

from helpers import make_text_response, make_tool_use_response
from ai_generator import AIGenerator


PATCH_TARGET = "ai_generator.anthropic.Anthropic"

SAMPLE_TOOLS = [
    {
        "name": "search_course_content",
        "description": "Search course materials",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }
]


@pytest.fixture
def generator_and_mock():
    with patch(PATCH_TARGET) as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="claude-test")
        yield gen, mock_client


# ── 2.1 end_turn returns text directly ───────────────────────────────────────

def test_generate_response_returns_text_on_end_turn(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Paris is the capital.")

    result = gen.generate_response(query="What is the capital of France?")

    assert result == "Paris is the capital."
    mock_client.messages.create.assert_called_once()


# ── 2.2 No tools → no tools/tool_choice in params ────────────────────────────

def test_generate_response_no_tools_omits_tool_params(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="General question")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


# ── 2.3 With tools → tools and tool_choice=auto in params ────────────────────

def test_generate_response_with_tools_adds_tool_params(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="Course question", tools=SAMPLE_TOOLS)

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["tools"] == SAMPLE_TOOLS
    assert call_kwargs["tool_choice"] == {"type": "auto"}


# ── 2.4 System prompt sent as top-level `system=` param ──────────────────────

def test_generate_response_system_prompt_not_in_messages(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="Question")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    messages = call_kwargs["messages"]
    assert all(m["role"] != "system" for m in messages)


# ── 2.5 History appended to system prompt ────────────────────────────────────

def test_generate_response_appends_history_to_system_prompt(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="Q", conversation_history="User: Hello\nAssistant: Hi")

    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert AIGenerator.SYSTEM_PROMPT in system
    assert "Previous conversation:" in system
    assert "User: Hello\nAssistant: Hi" in system


# ── 2.6 No history → system prompt verbatim ──────────────────────────────────

def test_generate_response_no_history_sends_system_prompt_verbatim(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="Q")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT


# ── 2.7 tool_use triggers two-turn loop ──────────────────────────────────────

def test_generate_response_tool_use_triggers_tool_execution(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response(
        tool_name="search_course_content",
        tool_id="toolu_01",
        tool_input={"query": "RAG systems", "course_name": "ML Course"},
    )
    second = make_text_response("RAG stands for Retrieval-Augmented Generation.")
    mock_client.messages.create.side_effect = [first, second]

    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "RAG is a retrieval technique."

    result = gen.generate_response(
        query="What is RAG?", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
    )

    assert result == "RAG stands for Retrieval-Augmented Generation."
    assert mock_client.messages.create.call_count == 2
    mock_tool_manager.execute_tool.assert_called_once_with(
        "search_course_content", query="RAG systems", course_name="ML Course"
    )


# ── 2.9 Round 2 message structure: [user, assistant, user(tool_result)] ──────

def test_handle_tool_execution_message_structure(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "test"})
    second = make_text_response("Final answer.")
    mock_client.messages.create.side_effect = [first, second]
    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Tool result."

    gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
    assert len(second_call_messages) == 3
    assert second_call_messages[0]["role"] == "user"
    assert second_call_messages[1]["role"] == "assistant"
    assert second_call_messages[2]["role"] == "user"

    tool_result_content = second_call_messages[2]["content"]
    assert isinstance(tool_result_content, list)
    assert tool_result_content[0]["type"] == "tool_result"
    assert tool_result_content[0]["tool_use_id"] == "toolu_01"
    assert "Tool result." in tool_result_content[0]["content"]


# ── 2.10 Only tool_use blocks are executed ────────────────────────────────────

def test_handle_tool_execution_skips_non_tool_blocks(generator_and_mock):
    gen, mock_client = generator_and_mock

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Let me search..."

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "search_course_content"
    tool_block.id = "toolu_01"
    tool_block.input = {"query": "test"}

    first = MagicMock()
    first.stop_reason = "tool_use"
    first.content = [text_block, tool_block]

    second = make_text_response("Final answer.")
    mock_client.messages.create.side_effect = [first, second]

    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Result."

    gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    assert mock_tool_manager.execute_tool.call_count == 1


# ── 2.11 tool_use with no tool_manager → AttributeError  [EXPECTS TO FAIL — B2]

def test_generate_response_tool_use_without_tool_manager_raises(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "test"})
    mock_client.messages.create.return_value = first

    with pytest.raises((AttributeError, ValueError)):
        gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=None)


# ── 2.12 base_params (model/temperature/max_tokens) in first API call ─────────

def test_generate_response_includes_base_params(generator_and_mock):
    gen, mock_client = generator_and_mock
    mock_client.messages.create.return_value = make_text_response("Answer.")

    gen.generate_response(query="Q")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-test"
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["max_tokens"] == 800


# ── 2.13 Two tool rounds → 3 API calls, both tools executed ──────────────────

def test_two_tool_rounds_makes_three_api_calls(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "first query"})
    second = make_tool_use_response("get_course_outline", "toolu_02", {"course_name": "ML Course"})
    third = make_text_response("Final answer using both tool results.")
    mock_client.messages.create.side_effect = [first, second, third]

    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Tool result."

    result = gen.generate_response(
        query="Compare topics", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
    )

    assert result == "Final answer using both tool results."
    assert mock_client.messages.create.call_count == 3
    assert mock_tool_manager.execute_tool.call_count == 2


# ── 2.14 Round 2 API call includes tools so Claude can decide to use one ──────

def test_second_round_call_includes_tools(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "test"})
    second = make_text_response("Answer after one round.")
    mock_client.messages.create.side_effect = [first, second]
    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Tool result."

    gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    assert "tools" in second_call_kwargs
    assert "tool_choice" in second_call_kwargs


# ── 2.15 Tool failure → error injected as tool_result, synthesis call made ───

def test_tool_failure_breaks_loop_and_synthesizes(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "test"})
    synthesis = make_text_response("Answer after tool failure.")
    mock_client.messages.create.side_effect = [first, synthesis]

    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.side_effect = Exception("search failed")

    result = gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    assert result == "Answer after tool failure."
    assert mock_client.messages.create.call_count == 2
    assert mock_tool_manager.execute_tool.call_count == 1

    synthesis_kwargs = mock_client.messages.create.call_args_list[1][1]
    assert "tools" not in synthesis_kwargs

    tool_result_message = synthesis_kwargs["messages"][2]
    assert "Tool execution failed" in tool_result_message["content"][0]["content"]


# ── 2.16 Single tool round returns text directly — no extra synthesis call ────

def test_claude_stops_after_round_one_returns_text(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "test"})
    second = make_text_response("Answer after one tool round.")
    mock_client.messages.create.side_effect = [first, second]
    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Tool result."

    result = gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    assert result == "Answer after one tool round."
    assert mock_client.messages.create.call_count == 2


# ── 2.17 After two tool rounds, synthesis call receives all 5 messages ────────

def test_two_rounds_full_message_accumulation(generator_and_mock):
    gen, mock_client = generator_and_mock
    first = make_tool_use_response("search_course_content", "toolu_01", {"query": "q1"})
    second = make_tool_use_response("get_course_outline", "toolu_02", {"course_name": "Course"})
    third = make_text_response("Final.")
    mock_client.messages.create.side_effect = [first, second, third]
    mock_tool_manager = MagicMock()
    mock_tool_manager.execute_tool.return_value = "Result."

    gen.generate_response(query="Q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager)

    synthesis_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
    assert len(synthesis_messages) == 5
    roles = [m["role"] for m in synthesis_messages]
    assert roles == ["user", "assistant", "user", "assistant", "user"]


# ── 2.18 System prompt no longer contains the one-tool-per-query limit ────────

def test_system_prompt_allows_sequential_tool_calls():
    assert "One tool call per query maximum" not in AIGenerator.SYSTEM_PROMPT
    assert "sequential" in AIGenerator.SYSTEM_PROMPT.lower() or "2 sequential" in AIGenerator.SYSTEM_PROMPT
