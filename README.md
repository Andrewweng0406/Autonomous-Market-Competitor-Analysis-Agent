# Autonomous Market & Competitor Analysis Agent

An AI agent that takes a business idea, product concept, or company name and
returns a structured, evidence-backed market & competitor analysis — SWOT,
competitor breakdown, market trends, and a polished Markdown report — by
planning a research strategy, searching the live web, and synthesizing the
results with Claude.

**Status: Phase 1 (foundational architecture).** The backend is a complete,
runnable skeleton: FastAPI + native Anthropic tool calling, async task
execution, a real (optional) web search integration, and a 43-test suite.
The frontend ("Meridian") is a fully designed Next.js client — hero intake
form, live streaming progress, and a structured report view (SWOT quadrants,
competitor cards, sourced trends, Markdown/JSON toggle) — wired against the
exact backend contract below.

## How it works

1. You submit a subject (idea / product / company) via the API or UI.
2. The agent (`backend/app/agent/agent.py`) plans its research and calls the
   `web_search` tool as many times as it needs — real results via
   [Tavily](https://tavily.com) if configured, otherwise clearly-labeled mock
   data so the backend runs out of the box.
3. Once it has enough evidence, it calls a `submit_final_report` tool with a
   structured payload (SWOT, competitors, trends, sources, and a full
   Markdown report) — validated against a Pydantic schema.
4. The frontend polls or streams progress and renders the final report.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design
rationale (why a manual tool-use loop, why SSE + polling, how the async
pipeline is structured, and the production upgrade path).

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Agent orchestration | Native Anthropic tool calling (manual loop) | No beta SDK dependency; full control over progress reporting and the JSON output contract |
| LLM | Claude (`claude-sonnet-5` by default) | Adaptive thinking + effort control for research-heavy reasoning; cheap/fast for iterating — swap to `claude-opus-4-8` for max quality |
| Backend | FastAPI + Pydantic v2 | Async-native, typed, automatic OpenAPI docs at `/docs` |
| Search | Tavily API (optional; mock fallback) | Purpose-built for LLM agent search, simple REST API |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind v4 | Fast to iterate on, SSE-friendly, easy to deploy |
| Async task handling | In-memory `TaskManager` + SSE / polling | See ARCHITECTURE.md for the reasoning and the production swap-out path |

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, exception handlers, startup
│   │   ├── config.py               # Settings (env vars / .env)
│   │   ├── api/
│   │   │   └── routes.py           # /api/analyze, /api/status, /api/stream, /api/health
│   │   ├── agent/
│   │   │   ├── agent.py            # Core tool-use loop (MarketAnalysisAgent)
│   │   │   ├── prompts.py          # System prompt (elite VC analyst persona)
│   │   │   └── tools.py            # web_search + submit_final_report tool schemas/impl
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response/report models
│   │   ├── services/
│   │   │   └── task_manager.py     # Background task execution, progress pub/sub
│   │   └── core/
│   │       ├── exceptions.py
│   │       └── logging.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Phase orchestration: form → progress → report
│   │   ├── layout.tsx              # Fonts, metadata, theme provider (defaults to light)
│   │   └── globals.css             # Tailwind v4 theme tokens (light/dark)
│   ├── components/
│   │   ├── analysis-form.tsx       # Hero intake form (subject/type/depth/context)
│   │   ├── progress-view.tsx       # Live SSE progress with polling fallback
│   │   ├── report-view.tsx         # Structured report + Markdown/JSON toggle
│   │   ├── swot-grid.tsx           # SWOT quadrants
│   │   ├── competitor-card.tsx     # Competitor cards
│   │   └── ui/                     # Base button primitive (shadcn-style)
│   ├── lib/api.ts                  # Typed backend client (fetch + SSE + polling)
│   ├── package.json
│   └── .env.local.example
└── docs/
    └── ARCHITECTURE.md
```

## Getting started

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (required).
# TAVILY_API_KEY is optional — without it, web_search returns mock data.

uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs, or:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"subject": "A subscription box for artisanal coffee", "subject_type": "idea", "depth": "standard"}'
# => {"task_id": "...", "status": "pending", ...}

curl http://localhost:8000/api/status/<task_id>
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000
npm run dev
```

Visit `http://localhost:3000`, enter a business idea, and watch the live
progress stream in as the agent researches and reports back. Click "view a
sample report" on the form screen to preview the report UI instantly with
static sample data — no backend call required.

### Docker (backend only)

```bash
cd backend
docker build -t market-analysis-agent-backend .
docker run --env-file .env -p 8000:8000 market-analysis-agent-backend
```

## Configuration reference

See `backend/.env.example` for the full list. The only required variable is
`ANTHROPIC_API_KEY`. Key optional ones:

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Model used for the agent — swap to `claude-opus-4-8` for max reasoning quality once you're past prototyping |
| `ANTHROPIC_EFFORT` | `high` | `low` \| `medium` \| `high` \| `xhigh` \| `max` — thinking/tool-use depth |
| `TAVILY_API_KEY` | _(unset)_ | Enables real web search; falls back to mock data if unset |
| `MAX_AGENT_ITERATIONS` | `10` | Safety cap on the tool-use loop |
| `CORS_ALLOW_ORIGINS_RAW` | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `RATE_LIMIT_PER_MINUTE` | `5` | Max `/api/analyze` calls per client IP per minute (`0` disables) |
| `TASK_TTL_SECONDS` | `3600` | How long a finished task's result stays queryable before it's swept |

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Tests mock the Anthropic client entirely (no real API calls, no cost) and
cover: schema validation, the search tool + dispatcher, the agent's tool-use
loop (success, schema-validation retry, refusal, truncation, max-iterations),
task lifecycle + cleanup, the rate limiter, and the API routes end-to-end via
FastAPI's `TestClient`.

## What's next (Phase 2 ideas)

- Persist tasks in Redis/Postgres instead of in-memory (see ARCHITECTURE.md)
- Move agent execution to a dedicated worker queue for horizontal scaling
- Add authentication + per-user rate limiting
- Export reports as PDF/Notion/Slack
- Add a "compare two ideas side by side" mode
