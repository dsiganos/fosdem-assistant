"""FOSDEM assistant with support for local (MLX, Ollama) and cloud (Anthropic) LLMs."""

import json
import re
from typing import Generator

from config import (
    LLM_PROVIDER,
    MLX_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    ANTHROPIC_MODEL,
    SYSTEM_PROMPT,
)
from schedule.models import Schedule
from storage.preferences import PreferencesManager

from .tools import TOOLS, ToolExecutor


def get_tools_description() -> str:
    """Generate a text description of available tools for the system prompt."""
    lines = ["You have access to these tools:\n"]
    for tool in TOOLS:
        params = tool["input_schema"].get("properties", {})
        required = tool["input_schema"].get("required", [])
        param_strs = []
        for name, info in params.items():
            req = "(required)" if name in required else "(optional)"
            param_strs.append(f"    - {name}: {info.get('description', '')} {req}")
        params_text = "\n".join(param_strs) if param_strs else "    (no parameters)"
        lines.append(f"**{tool['name']}**: {tool['description']}\n  Parameters:\n{params_text}\n")
    return "\n".join(lines)


def get_mlx_system_prompt() -> str:
    """Build the system prompt for MLX models with tool instructions."""
    tools_desc = get_tools_description()
    return f"""{SYSTEM_PROMPT}

{tools_desc}

When you need to use a tool, output a JSON block in this exact format:
```tool
{{"tool": "tool_name", "args": {{"param1": "value1"}}}}
```

After I execute the tool, I'll provide the result. Then continue your response to the user.
Only use one tool at a time. Wait for the result before using another tool.
If you don't need a tool, just respond normally without the tool block.
"""


def convert_tools_to_openai_format(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool format to OpenAI function format."""
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        })
    return openai_tools


class MLXAssistant:
    """Assistant using local MLX (Apple Silicon optimized)."""

    def __init__(self, schedule: Schedule, preferences: PreferencesManager):
        from mlx_lm import load, generate
        self.load = load
        self.generate = generate
        self.model = None
        self.tokenizer = None
        self.model_name = MLX_MODEL
        self.schedule = schedule
        self.preferences = preferences
        self.tool_executor = ToolExecutor(schedule, preferences)
        self.conversation: list[dict] = []
        self.system_prompt = get_mlx_system_prompt()

    def _ensure_model_loaded(self):
        """Lazy load the model on first use."""
        if self.model is None:
            print(f"Loading model {self.model_name}...")
            self.model, self.tokenizer = self.load(self.model_name)
            print("Model loaded!")

    def _build_prompt(self) -> str:
        """Build the full prompt from conversation history."""
        messages = [{"role": "system", "content": self.system_prompt}] + self.conversation
        return self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    def _parse_tool_call(self, text: str) -> tuple[str, dict | None, dict | None]:
        """Parse text for tool calls. Returns (clean_text, tool_name, tool_args)."""
        # Look for ```tool ... ``` blocks
        pattern = r'```tool\s*\n?\s*(\{.*?\})\s*\n?```'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            try:
                tool_json = json.loads(match.group(1))
                tool_name = tool_json.get("tool")
                tool_args = tool_json.get("args", {})
                # Remove the tool block from text
                clean_text = text[:match.start()] + text[match.end():]
                return clean_text.strip(), tool_name, tool_args
            except json.JSONDecodeError:
                pass

        return text, None, None

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """Send a message and stream the response."""
        self._ensure_model_loaded()

        self.conversation.append({
            "role": "user",
            "content": user_message
        })

        max_tool_iterations = 5

        for _ in range(max_tool_iterations):
            prompt = self._build_prompt()

            # Generate response
            response = self.generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=1024,
                verbose=False,
            )

            # Parse for tool calls
            clean_text, tool_name, tool_args = self._parse_tool_call(response)

            # Yield the clean text (without tool block)
            if clean_text:
                yield clean_text

            # Add assistant response to conversation
            self.conversation.append({
                "role": "assistant",
                "content": response
            })

            # If there's a tool call, execute it
            if tool_name:
                result = self.tool_executor.execute(tool_name, tool_args or {})

                # Add tool result as user message
                self.conversation.append({
                    "role": "user",
                    "content": f"Tool result for {tool_name}:\n{result}"
                })

                yield "\n"
                continue

            # No tool call, we're done
            break

    def reset_conversation(self) -> None:
        """Clear the conversation history."""
        self.conversation = []


class OllamaAssistant:
    """Assistant using local Ollama."""

    def __init__(self, schedule: Schedule, preferences: PreferencesManager):
        from openai import OpenAI
        self.client = OpenAI(
            base_url=f"{OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )
        self.model = OLLAMA_MODEL
        self.schedule = schedule
        self.preferences = preferences
        self.tool_executor = ToolExecutor(schedule, preferences)
        self.conversation: list[dict] = []
        self.openai_tools = convert_tools_to_openai_format(TOOLS)

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """Send a message and stream the response."""
        self.conversation.append({
            "role": "user",
            "content": user_message
        })

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.conversation

        while True:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.openai_tools,
                stream=True,
            )

            collected_content = ""
            collected_tool_calls = []
            current_tool_call = None

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                if delta.content:
                    collected_content += delta.content
                    yield delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            while len(collected_tool_calls) <= tc.index:
                                collected_tool_calls.append({
                                    "id": "",
                                    "function": {"name": "", "arguments": ""}
                                })
                            current_tool_call = collected_tool_calls[tc.index]

                        if tc.id:
                            current_tool_call["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                current_tool_call["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                current_tool_call["function"]["arguments"] += tc.function.arguments

            assistant_message = {"role": "assistant", "content": collected_content or None}
            if collected_tool_calls:
                assistant_message["tool_calls"] = [
                    {"id": tc["id"], "type": "function", "function": tc["function"]}
                    for tc in collected_tool_calls
                ]

            self.conversation.append(assistant_message)
            messages.append(assistant_message)

            if collected_tool_calls:
                for tc in collected_tool_calls:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}

                    result = self.tool_executor.execute(func_name, func_args)
                    tool_result_msg = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                    self.conversation.append(tool_result_msg)
                    messages.append(tool_result_msg)

                yield "\n"
                continue

            break

    def reset_conversation(self) -> None:
        """Clear the conversation history."""
        self.conversation = []


class AnthropicAssistant:
    """Assistant using Anthropic Claude API."""

    def __init__(self, schedule: Schedule, preferences: PreferencesManager):
        import anthropic
        self.client = anthropic.Anthropic()
        self.schedule = schedule
        self.preferences = preferences
        self.tool_executor = ToolExecutor(schedule, preferences)
        self.conversation: list[dict] = []

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """Send a message and stream the response."""
        self.conversation.append({
            "role": "user",
            "content": user_message
        })

        while True:
            with self.client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.conversation
            ) as stream:
                response_content = []

                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield event.delta.text

                final_message = stream.get_final_message()

                for block in final_message.content:
                    response_content.append(block)

                self.conversation.append({
                    "role": "assistant",
                    "content": response_content
                })

                if final_message.stop_reason == "tool_use":
                    tool_results = []
                    for block in response_content:
                        if block.type == "tool_use":
                            result = self.tool_executor.execute(
                                block.name,
                                block.input
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    self.conversation.append({
                        "role": "user",
                        "content": tool_results
                    })

                    yield "\n"
                    continue

                break

    def reset_conversation(self) -> None:
        """Clear the conversation history."""
        self.conversation = []


def FosdemAssistant(schedule: Schedule, preferences: PreferencesManager):
    """Factory function to create the appropriate assistant based on config."""
    if LLM_PROVIDER == "mlx":
        return MLXAssistant(schedule, preferences)
    elif LLM_PROVIDER == "ollama":
        return OllamaAssistant(schedule, preferences)
    else:
        return AnthropicAssistant(schedule, preferences)
