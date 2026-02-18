import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for searching course information.

Tool Usage:
- **get_course_outline**: Use for outline, structure, or lesson-list questions about a course. Returns the course title, course link, and complete numbered lesson list.
- **search_course_content**: Use for questions about specific course content or detailed educational materials.
- **Sequential tool use**: You may call tools in up to two sequential rounds when the result of one tool informs the next search (e.g. get a course outline, then search a specific lesson). Do not repeat the same call with the same arguments.
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using a tool
- **Outline / structure questions** (e.g. "what lessons does X have?", "show me the outline of X"): Use get_course_outline, then present the course title, link, and each lesson number and title
- **Course-specific content questions**: Use search_course_content, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to MAX_TOOL_ROUNDS sequential tool-call rounds before a
        final no-tools synthesis call.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]
        response = None

        for _round in range(self.MAX_TOOL_ROUNDS):
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            response = self.client.messages.create(**api_params)

            # Claude answered directly or no tool manager — return immediately
            if response.stop_reason != "tool_use" or not tool_manager:
                return response.content[0].text

            # Execute all tool calls in this round
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as exc:
                        result = f"Tool execution error: {exc}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        # Rounds exhausted — one final call WITHOUT tools for synthesis
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
