# Tool Recommender

An assistant that recommends Galaxy tools using semantic search over an Upstash Vector index and an LLM with a bound tool. Conversations and tool-call transcripts are stored in MongoDB.

## Highlights
- Indexes Galaxy tool metadata in Upstash Vector for fast, semantic lookup.
- Chatbot uses a LangChain tool to fetch relevant tools during a conversation.
- Clean CLI with colors, shows tool data before the agent’s reply, and supports screen clearing.

## Architecture
- Chat + tool dispatch: [src/chatbot.py](src/chatbot.py)
- CLI interface: [src/ui.py](src/ui.py)
- Tool search wrapper: [src/tools/toolSearch.py](src/tools/toolSearch.py)
- Vector ingest/query: [src/rag/ingest.py](src/rag/ingest.py), [src/rag/query.py](src/rag/query.py)
- External service integrations: [src/lib/galaxy.py](src/lib/galaxy.py), [src/lib/upstash.py](src/lib/upstash.py), [src/lib/db.py](src/lib/db.py)
- Message store helpers: [src/utils/memory.py](src/utils/memory.py)
- Environment loading: [src/config/env.py](src/config/env.py)

## Requirements
- Python 3.10+
- MongoDB (local or remote)
- Galaxy URL + API key
- Upstash Vector (REST URL + token)
- An LLM provider:
    - OpenRouter: `OPEN_ROUTER_API=https://openrouter.ai/api/v1` and `OPEN_ROUTER_API_KEY=...`
    - Or OpenAI: switch the code to use `OPENAI_API_KEY` and native OpenAI endpoints (see notes below).

## Configuration (.env)
Create a `.env` at the repo root:

```
# Mongo
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=tool-recommender

# Galaxy
GALAXY_URL=https://usegalaxy.org
GALAXY_API_KEY=your_galaxy_api_key

# Upstash Vector
UPSTASH_VECTOR_REST_URL=https://your-upstash-url
UPSTASH_VECTOR_REST_TOKEN=your_upstash_token

# LLM (OpenRouter)
OPEN_ROUTER_API=https://openrouter.ai/api/v1
OPEN_ROUTER_API_KEY=your_openrouter_key

# Optional model override
OPENAI_MODEL=gpt-4o-mini
```

If you prefer OpenAI instead of OpenRouter, you can update `build_llm()` in [src/chatbot.py](src/chatbot.py) to use:

```python
ChatOpenAI(model=model_name, temperature=temperature)  # reads OPENAI_API_KEY from env
```

and set in `.env`:

```
OPENAI_API_KEY=sk-...
```

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If pip times out, retry with a longer timeout:
```bash
pip install --default-timeout 120 --retries 3 -r requirements.txt
```

## Ingest Galaxy tools (build the index)
This pulls Galaxy tools and upserts them into Upstash Vector.

```bash
python -m src.rag.ingest
```

## Run the CLI chatbot
Start an interactive session:

```bash
python -m src.ui
```

Commands inside the CLI:
- `/help` – brief usage
- `/clear` or `/cls` – clear the screen and header
- `/color` – enable colored output
- `/mono` – disable colored output
- `/exit` or `/quit` – leave the session

Behavior:
- The UI prints your message in color.
- When the agent calls a tool, it prints “Calling tool …” and shows the tool data (JSON highlighted) before the agent’s final reply.

## Programmatic usage
Query tools directly:

```bash
python - <<'PY'
from src.rag.query import query_tools

results = query_tools("align sequencing reads", top_k=3)
for r in results:
        meta = getattr(r, "metadata", {}) or {}
        print(meta.get("name"), meta.get("version"))
PY
```

Chat turn from code:

```bash
python - <<'PY'
from src.chatbot import run_chat

reply = run_chat("Find a Galaxy tool for sequence alignment", model="gpt-4o-mini")
print(reply)
PY
```

## Data & persistence
- Messages are stored in the `messages` collection under `DATABASE_NAME`.
- The chat reconstruction skips stored tool payloads to keep OpenAI/OpenRouter message sequences valid.

## Troubleshooting
- Pip dependency conflict (async-timeout): this repo pins `async-timeout==4.0.2` to satisfy LangChain on Python 3.10.
- Pip timeout: use `--default-timeout 120 --retries 3`.
- Invalid message role (OpenAI 400): old tool messages can violate ordering; the chat history builder skips orphan tool messages. If needed, clear history:
    ```bash
    mongosh --eval 'db.messages.drop()' "$DATABASE_NAME"
    ```
- Tool call issues: ensure `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN` are set and the ingest step completed.
- Galaxy API failures: verify `GALAXY_URL` and `GALAXY_API_KEY`.
- OpenRouter auth: set both `OPEN_ROUTER_API` and `OPEN_ROUTER_API_KEY`.

## Notes for developers
- The bound tool is declared in [src/chatbot.py](src/chatbot.py) and named `tool_search_tool` to avoid name collisions with the Python function in [src/tools/toolSearch.py](src/tools/toolSearch.py).
- If you switch providers, update `build_llm()` accordingly and ensure the right env vars are set.
- The UI in [src/ui.py](src/ui.py) avoids heavy box-drawing and focuses on readable output with subtle coloring.
