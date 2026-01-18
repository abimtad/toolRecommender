from rich.progress import track
from src.lib.galaxy import fetch_galaxy_tools
from src.lib.upstash import index


def upsert_tools(tools):
    """Embed and upsert tools into Upstash Vector"""
    total = len(list(tools))

    for tool in track(tools, total=total, description="Indexing tools...", transient=True):
        tool_id = tool.get("id")
        tool_name = tool.get("name")
        tool_description = tool.get("description") or ""
        text_to_embed = f"{tool_name}. {tool_description}"

        print("tool_id", tool_id)

        metadata = {
            "id": tool_id,
            "name": tool_name,
            "description": tool_description,
            "version": tool.get("version"),
            "owner": tool.get("owner"),
        }

        try:
            index.upsert([
                {
                    "id": tool_id,     # Unique ID
                    "data": text_to_embed,  # Text to embed
                    "metadata": metadata
                }
            ])
        except Exception as e:
            print(f"Failed to upsert tool {tool_name}: {e}")


def main(period_seconds: int = 3600):
    """Main loop to periodically fetch and index Galaxy tools"""
    tools = fetch_galaxy_tools()
    upsert_tools(tools)


if __name__ == "__main__":
    main()
