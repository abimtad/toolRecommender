import json
from src.lib.upstash import index


def query_tools(query: str, top_k: int = 5):
    """
    Query the Upstash vector index.
    Returns the closest matching tools.
    """

    result = index.query(
        data=query,
        top_k=top_k,
        include_metadata=True,
        include_data=True,
    )

    return result


if __name__ == "__main__":
    # Test run
    results = query_tools("align sequencing data", top_k=3)

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
    print(json.dumps(formatted, indent=2))
