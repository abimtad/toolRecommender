import json
import os
from typing import Any, List, Sequence, Tuple, Callable, Optional
from src.config.env import OPEN_ROUTER_API, OPEN_ROUTER_API_KEY

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from src.tools.toolSearch import tool_search as py_tool_search
from src.utils.memory import add_messages, get_messages, save_tool_response

SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the `tool_search` function when you need "
    "to look up Galaxy tools or related information. Keep replies concise and "
    "cite tool results clearly. If a tool call is not needed, answer directly."
)


@tool
def tool_search_tool(query: str, top_k: int = 5) -> str:
    """Search Galaxy tools using the vector index and return JSON results."""
    return py_tool_search(query=query, top_k=top_k)


def build_llm(model: str | None = None, temperature: float = 0) -> ChatOpenAI:
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=OPEN_ROUTER_API_KEY,
        base_url=OPEN_ROUTER_API,
    ).bind_tools([tool_search_tool])


def docs_to_lc_messages(docs: Sequence[dict]) -> List[BaseMessage]:
    """Simplify history: include only system/user/assistant content.

    Previously persisted tool metadata may not match the exact schema expected
    by the client, and is not needed for future turns. Skipping tool messages
    avoids invalid payloads (e.g., unexpected fields like 'index').
    """
    messages: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for doc in docs:
        role = doc.get("role")
        if role == "user":
            messages.append(HumanMessage(content=doc.get("content", "")))
        elif role == "assistant":
            messages.append(AIMessage(content=doc.get("content", "")))
        # Skip stored tool messages in reconstructed history
    return messages


def serialize_tool_calls(tool_calls: Any) -> List[dict]:
    serialized: List[dict] = []
    if not tool_calls:
        return serialized

    for idx, tc in enumerate(tool_calls):
        tc_id = getattr(tc, "id", None) or tc.get(
            "id") if isinstance(tc, dict) else None
        tc_type = getattr(tc, "type", None) or tc.get(
            "type") if isinstance(tc, dict) else None
        name = getattr(tc, "name", None)
        args = getattr(tc, "args", None)
        function = getattr(tc, "function", None)

        if isinstance(tc, dict):
            function = tc.get("function") or function
            if not name:
                name = tc.get("name") or (function or {}).get("name")
            if args is None:
                args = tc.get("args") or (function or {}).get("arguments")

        if isinstance(function, dict):
            name = name or function.get("name")
            args = args or function.get("arguments")

        args_text: str
        if isinstance(args, str):
            args_text = args
        else:
            try:
                args_text = json.dumps(args or {})
            except TypeError:
                args_text = str(args)

        serialized.append(
            {
                "index": idx,
                "id": tc_id,
                "type": tc_type or "function",
                "function": {
                    "name": name or "tool_search",
                    "arguments": args_text,
                },
            }
        )
    return serialized


def parse_arguments(raw_args: Any) -> dict:
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {"query": raw_args}
    return {}


def dispatch_tool_call(tc: Any) -> Tuple[str, str]:
    name = getattr(tc, "name", None)
    args = getattr(tc, "args", None)
    function = getattr(tc, "function", None)

    if isinstance(tc, dict):
        function = function or tc.get("function")
        name = name or tc.get("name") or (function or {}).get("name")
        args = args or tc.get("args") or (function or {}).get("arguments")

    parsed_args = parse_arguments(args)
    tool_name = name or "tool_search"

    if tool_name in {"tool_search", "search_tools", "tool_search_tool"}:
        query = parsed_args.get("query") or parsed_args.get("q") or ""
        top_k = parsed_args.get("top_k") or parsed_args.get("k") or 5
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        result = py_tool_search(query=query, top_k=top_k)
        return tool_name, result

    return tool_name, f"Unsupported tool: {tool_name}"


def store_ai_message(ai_msg: AIMessage):
    add_messages(
        [
            {
                "role": "assistant",
                "content": ai_msg.content or "",
                "tool_calls": serialize_tool_calls(ai_msg.tool_calls),
                "refusal": getattr(ai_msg, "refusal", None),
                "reasoning": getattr(ai_msg, "reasoning", None),
            }
        ]
    )


def run_chat(
    user_input: str,
    model: str | None = None,
    on_event: Optional[Callable[[dict], None]] = None,
) -> str:
    # Persist user message first so it becomes part of history
    add_messages([
        {
            "role": "user",
            "content": user_input,
        }
    ])

    history_docs = get_messages()
    messages = docs_to_lc_messages(history_docs)

    llm = build_llm(model=model)

    while True:
        ai_msg: AIMessage = llm.invoke(messages)
        store_ai_message(ai_msg)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            return ai_msg.content or ""

        for tc in ai_msg.tool_calls:
            tc_id = getattr(tc, "id", None)
            if tc_id is None and isinstance(tc, dict):
                tc_id = tc.get("id")

            # Preview tool call event to UI
            name = getattr(tc, "name", None)
            args = getattr(tc, "args", None)
            function = getattr(tc, "function", None)
            if isinstance(tc, dict):
                function = function or tc.get("function")
                name = name or tc.get("name") or (function or {}).get("name")
                args = args or tc.get("args") or (
                    function or {}).get("arguments")

            parsed_args = parse_arguments(args)
            tool_name = name or "tool_search"

            if on_event:
                try:
                    on_event({
                        "type": "tool_call",
                        "name": tool_name,
                        "args": parsed_args,
                        "id": str(tc_id or ""),
                    })
                except Exception:
                    pass

            _, tool_output = dispatch_tool_call(tc)

            # Persist tool result
            save_tool_response(tool_call_id=str(tc_id or ""),
                               tool_response=str(tool_output))

            # Feed back into the LLM
            messages.append(
                ToolMessage(
                    content=str(tool_output),
                    tool_call_id=str(tc_id or ""),
                )
            )

            # Notify UI of tool result
            if on_event:
                try:
                    on_event({
                        "type": "tool_result",
                        "name": tool_name,
                        "result": tool_output,
                        "id": str(tc_id or ""),
                    })
                except Exception:
                    pass


if __name__ == "__main__":
    response = run_chat(
        "Hello! Can you find me a tool for sequence alignment?")
    print(response)
