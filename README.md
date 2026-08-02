# single-vendor-ai

FastAPI + LangChain/LangGraph AI service for the single-vendor storefront:
customer RAG + tool-calling chatbot, and an admin analytics chatbot.


## Local setup (one-time)

```
uv venv
uv pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET (copy from
                        # single-vendor-backend/.env), OPENAI_API_KEY
```

## Run the dev server

```
uv run uvicorn app.main:app --reload --port 8001 --loop app.core.loop:loop_factory
```

The `--loop` flag forces SelectorEventLoop on Windows (required by the
durable checkpointer's psycopg async connection — see `app/core/memory.py`
and `app/core/loop.py`); harmless/no-op on other platforms. Don't drop it
even if the server seems to start fine without it — the checkpointer will
fail on its first real connection, not at boot.

Then `GET http://localhost:8001/health` should return `{"status": "ok"}`.

## Layout

See `ai-chatbot-plan.txt` section 3 for the full annotated project layout
and what belongs in each module. Every non-trivial file in `app/` currently
contains a `# TODO` comment pointing back to the relevant plan section —
that's the intended starting point for implementation, not missing files.
