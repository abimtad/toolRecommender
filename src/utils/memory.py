from datetime import datetime, timezone
from uuid import uuid4

from bson.objectid import ObjectId
from src.lib.db import db

messages_collection = db["messages"]


# --- Helper functions ---
def add_metadata(message: dict) -> dict:
    """Add ids and timestamps to a message before saving."""
    msg = message.copy()

    # Stable unique id for clients and logs
    msg.setdefault("id", str(uuid4()))

    # ISO timestamp for external consumers
    now = datetime.now(timezone.utc)
    msg.setdefault("createdAt", now.isoformat())

    # Internal fields for Mongo sorting/debugging
    msg.setdefault("_id", ObjectId())
    msg.setdefault("created_at", now)

    return msg


def remove_metadata(message: dict) -> dict:
    """Remove _id before returning messages."""
    msg = message.copy()
    msg.pop("_id", None)
    msg.pop("created_at", None)
    return msg


# --- Memory functions ---
def add_messages(messages: list[dict]):
    """Add messages to MongoDB collection."""
    docs = [add_metadata(m) for m in messages]
    if docs:
        messages_collection.insert_many(docs)


def get_messages() -> list[dict]:
    """Return all messages without _id."""
    docs = list(messages_collection.find({}).sort("created_at", 1))
    return [remove_metadata(d) for d in docs]


def save_tool_response(tool_call_id: str, tool_response: str):
    """Add a tool message to the DB with tool_call_id."""
    msg = {
        "role": "tool",
        "content": tool_response,
        "tool_call_id": tool_call_id,
    }
    add_messages([msg])


# --- Optional testing ---
if __name__ == "__main__":
    add_messages([{"role": "user", "content": "Hello"}])
    save_tool_response("12345", "Tool response example")
    all_msgs = get_messages()
    print(all_msgs)
