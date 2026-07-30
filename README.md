# single-vendor-ai

FastAPI + LangChain/LangGraph AI service for the single-vendor storefront:
customer RAG + tool-calling chatbot, and an admin analytics chatbot.


## Local setup

```
uv venv
uv pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET (copy from
                        # single-vendor-backend/.env), OPENAI_API_KEY
uv run uvicorn app.main:app --reload --port 8001
```

Then `GET http://localhost:8001/health` should return `{"status": "ok"}`.

## Layout

See `ai-chatbot-plan.txt` section 3 for the full annotated project layout
and what belongs in each module. Every non-trivial file in `app/` currently
contains a `# TODO` comment pointing back to the relevant plan section —
that's the intended starting point for implementation, not missing files.
