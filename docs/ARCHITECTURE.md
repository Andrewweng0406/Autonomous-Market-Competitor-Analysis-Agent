# Architecture

## Overview

```
┌─────────────┐      POST /api/analyze       ┌──────────────────┐
│   Next.js   │ ───────────────────────────▶ │     FastAPI       │
│  Frontend   │ ◀─────────────────────────── │   (main.py)       │
└─────────────┘   202 { task_id }             └────────┬─────────┘
      │                                                 │ asyncio.create_task
      │  GET /api/stream/{task_id}  (SSE)               ▼
      │  GET /api/status/{task_id}  (poll)     ┌──────────────────┐
      └────────────────────────────────────────▶│   TaskManager    │
                                                 │ (in-memory store)│
                                                 └────────┬─────────┘
                                                          │ agent.run()
                                                          ▼
                                                 ┌──────────────────┐
                                                 │ MarketAnalysis   │
                                                 │      Agent       │
                                                 │ (tool-use loop)  │
                                                 └───┬──────────┬───┘
                                        web_search    │          │  submit_final_report
                                                       ▼          ▼
                                            ┌────────────────┐  FinalReport
                                            │ Tavily Search  │  (validated JSON)
                                            │ API (or mock)  │
                                            └────────────────┘
```

## Why a manual tool-use loop instead of the SDK's beta tool runner?

The Anthropic Python SDK ships a beta `client.beta.messages.tool_runner()`
helper that automates the call → execute → feed-back loop. This skeleton
uses a **manual loop** (`app/agent/agent.py`) instead, for three reasons:

1. **Zero beta dependency.** The manual loop only uses the stable
   `client.messages.create()` endpoint.
2. **Full control over progress reporting.** Each tool call needs to notify
   `TaskManager` so the frontend can show "Searching: ..." in real time —
   easiest to wire up when you own the loop.
3. **Explicit termination condition.** Rather than parsing free-form text at
   the end of the conversation, the agent is required to call a
   `submit_final_report` tool with a schema matching `FinalReport`. This is a
   simple, reliable pattern for getting valid structured JSON out of an
   agentic loop — no output-parsing heuristics required.

If you later want the SDK's tool runner (e.g. to reduce boilerplate), see
`shared/tool-use-concepts.md` in the Claude API skill — the swap is
localized to `agent.py`.

## Async handling: why polling *and* streaming?

A market analysis can take anywhere from 30 seconds to a few minutes
(multiple web searches + a large synthesis call). A single blocking HTTP
request would hit browser/proxy timeouts and leave the frontend with no
feedback for the user. Two complementary approaches are implemented:

### 1. Background task + polling (`/api/analyze` + `/api/status/{task_id}`)

`POST /api/analyze` returns **immediately** (HTTP 202) with a `task_id`. The
actual agent run happens in an `asyncio.Task` scheduled via
`asyncio.create_task()` inside `TaskManager.create_task()`. The frontend (or
any client) then polls `GET /api/status/{task_id}` until `status` is
`completed` or `failed`. This is the simplest possible integration — it works
behind any proxy, requires no persistent connection, and is what the
`AnalyzeResponse` / `TaskStatusResponse` contract in the prompt was built
around.

**Why not just `await` the agent inside the request handler?** Because the
whole point of returning a `task_id` is to decouple the HTTP request/response
cycle from the agent's runtime — otherwise you're back to a multi-minute
blocking request.

### 2. Server-Sent Events (`/api/stream/{task_id}`)

For a more responsive UI, `GET /api/stream/{task_id}` streams progress
updates (`"Searching: ..."`, `"Analysis complete."`, etc.) as they happen,
using a plain `text/event-stream` response — no extra dependency, no
WebSocket handshake. `TaskManager` maintains a set of `asyncio.Queue`
subscribers per task; the agent's `on_progress` callback pushes messages into
those queues, and the SSE endpoint drains them into `data: {...}\n\n` frames.

The frontend (`frontend/lib/api.ts` → `subscribeToStream`) prefers SSE and
falls back to polling (`pollStatus`) if the `EventSource` connection errors
out (e.g. a corporate proxy that buffers streaming responses).

### Why not WebSockets?

WebSockets are the right choice when you need **bidirectional** communication
mid-task (e.g. the user interrupts or redirects the agent while it's
running). This agent is a fire-and-forget research task with one-way
progress updates, so SSE is simpler: it's plain HTTP (works through more
infrastructure unmodified), requires no extra client library, and
auto-reconnects natively via `EventSource`. If you later add interactivity
(steering the agent mid-run, human-in-the-loop tool approval), upgrading the
`/api/stream` endpoint to a WebSocket is the natural next step — see
`shared/tool-use-concepts.md`'s security note on gating tool execution for
the pattern.

## In-memory `TaskManager` — production upgrade path

The current `TaskManager` (`app/services/task_manager.py`) stores tasks in a
plain Python `dict` and runs the agent via `asyncio.create_task`. This is
correct and simple for a single-process deployment, but has two limits worth
knowing about before scaling:

- **No durability.** A process restart loses all in-flight and completed
  tasks. Swap in Redis (or Postgres) for the store.
- **Single-process only.** Multiple uvicorn workers / replicas would each
  have their own task dict, so a status poll could hit an instance that never
  ran the task. Move task execution to a real queue (Celery, arq, Dramatiq)
  once you need horizontal scaling.

The `TaskManager` interface is intentionally narrow (`create_task`,
`get_task`, `subscribe`, `unsubscribe`) so this swap is localized to one
file.

## Agent reasoning: adaptive thinking + effort

The agent calls Claude with `thinking: {"type": "adaptive", "display":
"summarized"}` and `output_config: {"effort": "high"}` (both configurable via
`ANTHROPIC_EFFORT`). Adaptive thinking lets the model decide when and how
much to reason before acting — useful here since some subjects need heavy
competitive research and others are more straightforward. Thinking blocks are
always appended back into the conversation unmodified, which is required by
the API when continuing a multi-turn tool-use conversation.
