# Tool Recommender

A lightweight assistant that finds Galaxy tools by embedding their metadata into an Upstash Vector index and answering queries via an LLM tool call. Chat history and tool call transcripts are stored in MongoDB so the assistant can persist conversations.

## What it does
- Fetches Galaxy tool metadata via BioBlend and indexes it into Upstash Vector for semantic search.
- Exposes a LangChain tool (`tool_search`) that the chatbot uses to retrieve relevant tools.
- Stores conversations and tool responses in MongoDB for history and debugging.

## Project layout
- Chat loop and tool dispatch: [src/chatbot.py](src/chatbot.py)
- Tool search wrapper: [src/tools/toolSearch.py](src/tools/toolSearch.py)
- Vector ingest/query: [src/rag/ingest.py](src/rag/ingest.py), [src/rag/query.py](src/rag/query.py)
- External services: [src/lib/galaxy.py](src/lib/galaxy.py), [src/lib/upstash.py](src/lib/upstash.py), [src/lib/db.py](src/lib/db.py)
- Message store helpers: [src/utils/memory.py](src/utils/memory.py)
- Environment loading: [src/config/env.py](src/config/env.py)

## Prerequisites
- Python 3.10+
- Access to a MongoDB instance
- Galaxy API URL and API key
- Upstash Vector database (REST URL and token)
- OpenAI API key (for ChatOpenAI); optional `OPENAI_MODEL` override

## Environment variables
Create a `.env` in the repo root with at least:

```
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=tool-recommender
GALAXY_URL=https://usegalaxy.org
GALAXY_API_KEY=your_galaxy_api_key
UPSTASH_VECTOR_REST_URL=https://your-upstash-url
UPSTASH_VECTOR_REST_TOKEN=your_upstash_token
OPENAI_API_KEY=sk-...
# Optional
OPENAI_MODEL=gpt-4o-mini
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Index Galaxy tools
This fetches Galaxy tools and upserts them into Upstash Vector.

```bash
python -m src.rag.ingest
```

## Query tools programmatically
```bash
python - <<'PY'
from src.rag.query import query_tools

results = query_tools("align sequencing reads", top_k=3)
for r in results:
    meta = getattr(r, "metadata", {}) or {}
    print(meta.get("name"), meta.get("version"))
PY
```

## Run a chat turn
The chat loop persists history in MongoDB and will call the vector tool when needed.

```bash
python - <<'PY'
from src.chatbot import run_chat

reply = run_chat("Find a Galaxy tool for sequence alignment", model="gpt-4o-mini")
print(reply)
PY
```

## How it works (flow)
1) [src/rag/ingest.py](src/rag/ingest.py) pulls tool metadata from Galaxy and writes embeddings to Upstash Vector.
2) [src/tools/toolSearch.py](src/tools/toolSearch.py) queries the vector index and formats matches.
3) [src/chatbot.py](src/chatbot.py) builds a ChatOpenAI model bound to the tool and loops, dispatching tool calls and saving all messages via [src/utils/memory.py](src/utils/memory.py).

## Notes
- The ingest script prints basic progress; rerun it to refresh the index.
- MongoDB stores message history in a `messages` collection under `DATABASE_NAME`.
- Error messages while upserting usually indicate missing Upstash credentials or network issues.
