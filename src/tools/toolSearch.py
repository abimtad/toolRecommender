import json
from typing import Any

from src.rag.query import query_tools


def _to_dict(obj: Any) -> dict:
    """Convert metadata objects (pydantic/attrs/plain) to dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    return {}


def tool_search(query: str, top_k: int = 5) -> str:
    """Search Galaxy tools via vector embeddings and return JSON text."""
    results: Any = query_tools(query=query, top_k=top_k)

    formatted = []
    for result in results:
        meta = _to_dict(getattr(result, "metadata", None))
        data_text = getattr(result, "data", None)

        formatted.append(
            {
                "name": meta.get("name"),
                "description": data_text,
                "version": meta.get("version"),
                "owner": meta.get("owner"),
            }
        )

    # Return as plain string representation (not JSON) per request
    return str(formatted)


__all__ = ["tool_search"]
