"""Simple CLI UI for chatting with the Galaxy tool recommender.

This version avoids heavy ANSI styling and panels by default,
and prints plain lines for user/agent turns. It also shows
when the agent calls tools.
"""

from __future__ import annotations

import argparse
import ast
import json
from typing import Optional
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.theme import Theme
from rich.syntax import Syntax

from src.chatbot import run_chat


THEME = Theme({
    "you": "bold bright_cyan",
    "agent": "bold bright_green",
    "tool": "bold bright_yellow",
    "data": "bold magenta",
    "accent": "grey58",
    "error": "bold red",
})

CONSOLE = Console(theme=THEME, no_color=False)

YOU_ICON = "👤"
AGENT_ICON = "🤖"
TOOL_ICON = "🔧"
DATA_ICON = "📦"


def _set_color(enabled: bool):
    """Toggle color output by recreating the console."""
    global CONSOLE
    CONSOLE = Console(theme=THEME, no_color=not enabled)


def _print_line(role: str, body: str, style: str | None = None, icon: str | None = None):
    icon_str = f"{icon} " if icon else ""
    if style:
        CONSOLE.print(f"[{style}]{role}[/] {icon_str}{body}")
    else:
        CONSOLE.print(f"{role} {icon_str}{body}")


def _erase_last_line():
    """Erase the last printed terminal line (best-effort)."""
    try:
        # Move up one line and clear it
        sys.stdout.write("\x1b[1A\x1b[2K")
        sys.stdout.flush()
    except Exception:
        pass


def _format_tool_data(raw: str) -> str:
    """Pretty-print tool data. Accepts JSON or Python-literal strings."""
    text = raw or ""
    # Try JSON first
    try:
        obj = json.loads(text)
        return json.dumps(obj, indent=2)
    except Exception:
        pass
    # Try Python literal (e.g., list/dict repr)
    try:
        obj = ast.literal_eval(text)
        return json.dumps(obj, indent=2)
    except Exception:
        pass
    # Fallback to raw
    return text


def chat_loop(model: Optional[str] = None):
    commands = WordCompleter(
        ["/exit", "/quit", "/help", "/clear", "/cls", "/color", "/mono"], ignore_case=True)
    session = PromptSession(history=InMemoryHistory())

    CONSOLE.rule("Galaxy Tool Recommender", style="accent")
    CONSOLE.print(
        "Type your question. Use /exit or Ctrl+D to quit. Use /clear to clear screen.")

    while True:
        try:
            user_text = session.prompt("You > ", completer=commands)
        except KeyboardInterrupt:
            CONSOLE.print("Press Ctrl+D or type /exit to quit.")
            continue
        except EOFError:
            CONSOLE.print("\nGoodbye!")
            break

        user_text = user_text.strip()
        if not user_text:
            continue

        lowered = user_text.lower()
        if lowered in {"/exit", "/quit"}:
            break
        if lowered in {"/clear", "/cls"}:
            CONSOLE.clear()
            CONSOLE.rule("Galaxy Tool Recommender", style="accent")
            continue
        if lowered == "/color":
            _set_color(True)
            CONSOLE.rule("Galaxy Tool Recommender", style="accent")
            continue
        if lowered == "/mono":
            _set_color(False)
            CONSOLE.rule("Galaxy Tool Recommender", style="accent")
            continue
        if lowered == "/help":
            CONSOLE.print(
                "Enter a message for the agent. /exit quits. /clear clears the screen.")
            continue

        # Remove the raw input line so only the colored output remains
        _erase_last_line()
        _print_line("You:", user_text, style="you", icon=YOU_ICON)

        try:
            def on_event(ev: dict):
                if ev.get("type") == "tool_call":
                    name = ev.get("name")
                    _print_line("Calling tool:",
                                f"{name}...", style="tool", icon=TOOL_ICON)
                elif ev.get("type") == "tool_result":
                    name = ev.get("name")
                    data = _format_tool_data(str(ev.get("result", "")))
                    # Show data BEFORE agent's final response
                    _print_line(
                        "Tool data:", f"{name} →", style="data", icon=DATA_ICON)
                    # Syntax-highlight JSON if possible
                    try:
                        syn = Syntax(
                            data, "json", theme="ansi_dark", line_numbers=False)
                        CONSOLE.print(syn)
                    except Exception:
                        CONSOLE.print(data)

            reply = run_chat(user_text, model=model, on_event=on_event)
        except Exception as exc:  # pragma: no cover
            _print_line("Error", str(exc))
            continue

        _print_line("Agent:", reply.strip(
        ) if reply else "(no response)", style="agent", icon=AGENT_ICON)


def main():
    parser = argparse.ArgumentParser(
        description="Chat with the Galaxy tool recommender")
    parser.add_argument(
        "--model", help="Override the model name for the session")
    args = parser.parse_args()

    chat_loop(model=args.model)


if __name__ == "__main__":
    main()
