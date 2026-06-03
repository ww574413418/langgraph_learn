# Agent RAG Learning Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current `ai_agent_rag_system` project into a production-oriented Agent + RAG learning path that ends with modern agent engineering skills: retrieval quality, tool design, streaming, durable workflows, memory, observability, evaluation, and safety.

**Architecture:** Keep the current layered architecture: FastAPI route -> application service -> RAG/Agent services -> database/infrastructure. Do not let LangGraph nodes, API routes, or UI components reach into low-level database details directly. Every learning phase must produce a working API, test, traceable data model, or frontend workflow.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis, pytest, Vue 3, LangChain, LangGraph, OpenAI Responses/Agents concepts, LangSmith-style observability/evaluation concepts.

---

## Current Baseline

The project already has:

- Knowledge base CRUD.
- Document registration and status fields.
- Text/Markdown loading.
- Markdown image placeholder extraction and `document_assets` persistence.
- Normal chunk and parent-child chunk indexing.
- Keyword retrieval as a teaching retrieval source.
- Parent-child backfill with orphan-child tracing.
- Context assembly with citation IDs and dynamic token budget.
- `POST /api/retrieval` route and `run_retrieval()` application service.
- Tests for keyword retrieval, parent-child backfill, orphan child handling, empty document scope, and token budget.

The project does not yet have:

- API-level tests for `POST /api/retrieval`.
- Embedding provider abstraction.
- pgvector column and vector search.
- Hybrid retrieval, RRF, or reranking.
- Asset resolution in retrieval responses.
- Chat/conversation persistence.
- SSE streaming and stop generation.
- LangGraph workflow, durable execution, human-in-the-loop, or memory.
- Agent event tables and trace UI.
- Eval datasets and regression quality tests.

## Guiding Standard

For this project, "best modern agent implementation" means:

- Tools are small, typed, observable, and permission-scoped.
- RAG retrieval is measurable: vector, keyword, hybrid, rerank, citations, and failure traces are visible.
- Agent execution is durable: a task can resume after interruption and does not repeat side effects.
- Memory is explicit: short-term conversation memory and long-term user/project memory are separate.
- Streaming is structured: token deltas, tool events, citations, assets, errors, and stop events are separate event types.
- Every agent run is observable: trace, node events, tool inputs/outputs, latency, token use, and errors are recorded.
- Quality is evaluated: curated datasets, retrieval recall, answer faithfulness, citation correctness, and regression tests.
- Safety is designed in: input validation, tool allowlists, output schema validation, sensitive trace controls, and data isolation.

## File Map

### Existing Files To Extend

- `app/api/router.py`: register new route modules.
- `app/api/routes/retrieval.py`: retrieval API endpoint.
- `app/services/retrieval_service.py`: application-level retrieval pipeline.
- `app/services/document_retrieval_service.py`: low-level retrieval and parent-child backfill.
- `app/services/context_assembly_service.py`: context selection, citation, truncation, token budget.
- `app/rag/retrieval_types.py`: internal retrieval dataclasses.
- `app/rag/token_budget.py`: token budget policy.
- `app/models/document_chunk.py`: future embedding/vector fields.
- `app/models/document_asset.py`: future asset-to-chunk linking and asset retrieval.
- `app/schemas/retrieval.py`: public retrieval request/response schema.
- `tests/test_document_retrieval.py`: retrieval behavior tests.
- `tests/test_token_budget.py`: budget policy tests.

### New Files To Add Later

- `tests/test_retrieval_api.py`: API-level retrieval tests.
- `app/rag/embeddings.py`: embedding provider interface and implementations.
- `app/rag/vector_store.py`: pgvector query boundary.
- `app/rag/hybrid.py`: score normalization, RRF, source merging.
- `app/rag/reranker.py`: rerank interface.
- `app/services/asset_resolution_service.py`: resolve image placeholders and linked assets.
- `app/models/conversation.py`: conversation persistence.
- `app/models/message.py`: message persistence.
- `app/models/agent_task.py`: agent task status.
- `app/models/agent_task_event.py`: traceable event log.
- `app/api/routes/chat.py`: non-streaming chat.
- `app/api/routes/stream.py`: SSE streaming chat.
- `app/api/routes/agent_tasks.py`: agent task APIs.
- `app/agents/state.py`: LangGraph state.
- `app/agents/tools.py`: typed tool wrappers around service methods.
- `app/agents/workflow.py`: compiled LangGraph workflow.
- `app/agents/nodes/router.py`: route task type.
- `app/agents/nodes/retriever.py`: call retrieval tools.
- `app/agents/nodes/analyzer.py`: analyze retrieved evidence.
- `app/agents/nodes/planner.py`: produce plan or answer.
- `app/agents/nodes/reviewer.py`: verify evidence and output quality.

---

## Phase 1: Stabilize Retrieval API

**Learning Goal:** Understand how a production API wraps an internal RAG pipeline without leaking low-level details.

**Files:**

- Modify: `app/services/retrieval_service.py`
- Modify: `app/api/routes/retrieval.py`
- Create: `tests/test_retrieval_api.py`

- [ ] **Step 1: Write API test for normal retrieval**

Create `tests/test_retrieval_api.py` with a test that inserts a knowledge base, indexed document, normal chunk, then posts to `/api/retrieval`.

Expected behavior:

- HTTP status is `200`.
- `context_text` contains the matching chunk.
- `citations[0].retrieval_mode == "normal"`.
- `trace.sources == ["keyword"]`.

- [ ] **Step 2: Write API test for empty knowledge base scope**

Add a test that creates one indexed document in knowledge base A, then queries knowledge base B with no indexed documents.

Expected behavior:

- HTTP status is `200`.
- `context_text == ""`.
- `citations == []`.
- `trace.total_hits == 0`.

- [ ] **Step 3: Run the API tests and confirm failures first**

Run:

```bash
pytest tests/test_retrieval_api.py -v
```

Expected before implementation: fail if route setup, test fixtures, or response conversion has gaps.

- [ ] **Step 4: Fix only the API boundary issues**

Only touch:

- `tests/test_retrieval_api.py`
- `app/api/routes/retrieval.py`
- `app/services/retrieval_service.py`

Do not modify vector search, Agent code, or frontend in this phase.

- [ ] **Step 5: Verify**

Run:

```bash
python -m py_compile app/services/retrieval_service.py app/api/routes/retrieval.py app/api/router.py
pytest tests/test_retrieval_api.py tests/test_document_retrieval.py tests/test_token_budget.py
```

Expected: all selected tests pass.

---

## Phase 2: Replace Teaching Keyword Search With pgvector Retrieval

**Learning Goal:** Learn how production RAG separates embedding generation, vector persistence, vector search, and retrieval result normalization.

**Files:**

- Create: `app/rag/embeddings.py`
- Create: `app/rag/vector_store.py`
- Modify: `app/models/document_chunk.py`
- Modify: `app/services/document_indexing_service.py`
- Modify: `app/services/document_retrieval_service.py`
- Create: Alembic migration for vector column and index
- Create: `tests/test_embeddings.py`
- Create: `tests/test_vector_retrieval.py`

- [ ] **Step 1: Design embedding provider interface**

Create an `EmbeddingProvider` protocol with:

```python
class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...
```

Start with a deterministic test provider for tests, not a live API call.

- [ ] **Step 2: Add vector persistence**

Add an embedding column to `document_chunks`.

Expected production considerations:

- store `embedding_model`
- store vector dimensions consistently
- avoid re-embedding unchanged chunks
- add an index appropriate for pgvector

- [ ] **Step 3: Add vector search source**

Add a function that returns `list[ChunkHit]` with:

- `retrieval_source="vector"`
- `raw_score`
- `normalized_score`
- stable rank

- [ ] **Step 4: Keep keyword search as a separate source**

Do not delete keyword search. Rename it conceptually as a sparse/lexical source used later by hybrid search.

- [ ] **Step 5: Verify**

Run:

```bash
pytest tests/test_embeddings.py tests/test_vector_retrieval.py tests/test_document_retrieval.py
```

Expected: deterministic vector tests pass without external network calls.

---

## Phase 3: Hybrid Retrieval, RRF, and Reranking

**Learning Goal:** Learn the retrieval quality stack used in stronger RAG systems: recall from multiple sources, merge, rerank, then assemble.

**Files:**

- Create: `app/rag/hybrid.py`
- Create: `app/rag/reranker.py`
- Modify: `app/rag/retrieval_types.py`
- Modify: `app/services/document_retrieval_service.py`
- Create: `tests/test_hybrid_retrieval.py`
- Create: `tests/test_reranker.py`

- [ ] **Step 1: Implement score normalization**

Normalize scores per source so vector and keyword scores can be compared safely.

- [ ] **Step 2: Implement reciprocal rank fusion**

RRF input:

```python
source_results: dict[str, list[ChunkHit]]
```

RRF output:

```python
list[ChunkHit]
```

Expected behavior:

- same chunk from multiple sources is merged
- source metadata is preserved
- final ordering is deterministic

- [ ] **Step 3: Add reranker interface**

Create a reranker protocol:

```python
class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[ContextCandidate], top_n: int) -> list[ContextCandidate]:
        ...
```

Use a deterministic fake reranker in tests.

- [ ] **Step 4: Connect hybrid mode**

Extend retrieval mode later as:

```python
RetrievalStrategy = Literal["keyword", "vector", "hybrid"]
```

Keep `RetrievalMode = Literal["normal", "parent_child"]` for chunk structure.

- [ ] **Step 5: Verify**

Run:

```bash
pytest tests/test_hybrid_retrieval.py tests/test_reranker.py tests/test_document_retrieval.py
```

Expected: hybrid retrieval improves recall without breaking parent-child backfill.

---

## Phase 4: Asset Resolution and Multimodal-Ready RAG

**Learning Goal:** Learn how production RAG keeps images/assets traceable without blindly injecting binary content into prompts.

**Files:**

- Create: `app/services/asset_resolution_service.py`
- Modify: `app/models/document_asset.py`
- Modify: `app/schemas/retrieval.py`
- Modify: `app/services/retrieval_service.py`
- Create: `tests/test_asset_resolution.py`

- [ ] **Step 1: Resolve asset placeholders from used candidates**

Input:

```python
used_candidates: list[ContextCandidate]
```

Output:

```python
list[ResolvedAsset]
```

The resolver must find placeholders such as `[IMAGE:asset_001]` and return the matching asset rows.

- [ ] **Step 2: Add linked asset resolution**

Support assets linked to context chunks or citation chunks.

- [ ] **Step 3: Add asset response schema**

Add asset fields to retrieval response:

- `asset_id`
- `document_id`
- `url`
- `asset_type`
- `alt_text`
- `placeholder`
- `source`

- [ ] **Step 4: Verify**

Run:

```bash
pytest tests/test_asset_resolution.py tests/test_retrieval_api.py
```

Expected: retrieval response can return text citations and image assets separately.

---

## Phase 5: Chat, Conversation, and Structured Streaming

**Learning Goal:** Learn how real LLM products manage conversation state, streaming events, cancellation, and citations.

**Files:**

- Create: `app/models/conversation.py`
- Create: `app/models/message.py`
- Create: `app/api/routes/chat.py`
- Create: `app/api/routes/stream.py`
- Create: `app/services/chat_service.py`
- Create: `app/services/streaming_service.py`
- Modify: `app/db/redis.py`
- Create: `tests/test_chat_service.py`
- Create: `tests/test_streaming_events.py`

- [ ] **Step 1: Persist conversations and messages**

Model the minimum production fields:

- conversation title
- message role
- message content
- parent/branch fields for regenerate later
- citations JSON
- created/updated timestamps

- [ ] **Step 2: Define SSE event schema**

Use separate event names:

- `run_started`
- `message_delta`
- `tool_event`
- `citation`
- `asset`
- `run_stopped`
- `done`
- `error`

- [ ] **Step 3: Implement stop generation status**

Redis key pattern:

```text
chat:run:{run_id}:status
```

Allowed statuses:

- `running`
- `cancelled`
- `completed`
- `failed`

- [ ] **Step 4: Verify**

Run:

```bash
pytest tests/test_chat_service.py tests/test_streaming_events.py
```

Expected: streaming emits structured events and stop status can interrupt at safe checkpoints.

---

## Phase 6: LangGraph Agent Workflow

**Learning Goal:** Learn modern graph-based agent orchestration: state, nodes, conditional edges, tool calls, event logs, retries, and reviewer loops.

**Files:**

- Create: `app/models/agent_task.py`
- Create: `app/models/agent_task_event.py`
- Create: `app/agents/state.py`
- Create: `app/agents/tools.py`
- Create: `app/agents/workflow.py`
- Create: `app/agents/nodes/router.py`
- Create: `app/agents/nodes/retriever.py`
- Create: `app/agents/nodes/analyzer.py`
- Create: `app/agents/nodes/planner.py`
- Create: `app/agents/nodes/reviewer.py`
- Create: `app/api/routes/agent_tasks.py`
- Create: `tests/test_agent_workflow.py`
- Create: `tests/test_agent_events.py`

- [ ] **Step 1: Define AgentState**

State must include:

- user input
- task type
- selected knowledge base
- retrieved citations
- draft output
- review result
- event IDs
- error state

- [ ] **Step 2: Wrap retrieval as a typed tool**

The Agent must call a stable tool wrapper, not raw SQL and not raw retrieval internals.

- [ ] **Step 3: Add workflow nodes**

Node responsibilities:

- router: classify task
- retriever: call retrieval tool
- analyzer: reason over retrieved evidence
- planner: produce answer or plan
- reviewer: check grounding and ask for revision when needed

- [ ] **Step 4: Persist agent events**

Every node writes:

- `task_id`
- `event_type`
- `node_name`
- `input_summary`
- `output_summary`
- `status`
- `duration_ms`
- `error_message`

- [ ] **Step 5: Verify**

Run:

```bash
pytest tests/test_agent_workflow.py tests/test_agent_events.py
```

Expected: the workflow can complete a retrieval-backed task and record node events.

---

## Phase 7: Durable Execution, Memory, and Human-in-the-Loop

**Learning Goal:** Learn the difference between a demo agent and a production agent that can pause, resume, recover, and remember.

**Files:**

- Modify: `app/agents/workflow.py`
- Create: `app/services/agent_checkpoint_service.py`
- Create: `app/services/memory_service.py`
- Create: `app/api/routes/agent_tasks.py`
- Create: `tests/test_agent_resume.py`
- Create: `tests/test_memory_service.py`

- [ ] **Step 1: Add thread IDs and checkpointing boundary**

Every agent run needs a stable `thread_id`.

- [ ] **Step 2: Make side effects idempotent**

Side effects include:

- database writes
- external model calls
- file writes
- tool calls that mutate state

Each side effect needs an idempotency key or task wrapper.

- [ ] **Step 3: Add human approval interrupt**

Use an approval checkpoint before high-impact actions such as:

- writing final analysis
- modifying persistent memory
- exporting a report

- [ ] **Step 4: Separate memory types**

Short-term memory:

- conversation thread state
- recent message history

Long-term memory:

- user preferences
- project facts
- reusable instructions

- [ ] **Step 5: Verify**

Run:

```bash
pytest tests/test_agent_resume.py tests/test_memory_service.py
```

Expected: an interrupted agent can resume without repeating completed side effects.

---

## Phase 8: Observability and Evaluation

**Learning Goal:** Learn how serious agent teams debug, measure, and improve agents after they appear to work.

**Files:**

- Create: `app/services/trace_service.py`
- Create: `app/services/evaluation_service.py`
- Create: `tests/fixtures/eval_retrieval_cases.jsonl`
- Create: `tests/test_retrieval_evaluation.py`
- Create: `tests/test_trace_events.py`

- [ ] **Step 1: Define trace schema**

Trace every production run with:

- run ID
- user query
- retrieval sources
- top-k
- used citations
- dropped candidates
- token budget
- latency
- error state

- [ ] **Step 2: Build retrieval eval dataset**

Each JSONL example should contain:

```json
{"query": "如何处理扫地机器人无法充电？", "expected_document": "故障排除.txt", "expected_terms": ["充电", "底座", "电源"]}
```

- [ ] **Step 3: Add deterministic retrieval metrics**

Metrics:

- recall@k
- expected document hit
- citation contains expected term
- empty result rate

- [ ] **Step 4: Add answer quality eval later**

After LLM answering exists, add:

- faithfulness
- citation support
- refusal when evidence is missing
- answer completeness

- [ ] **Step 5: Verify**

Run:

```bash
pytest tests/test_retrieval_evaluation.py tests/test_trace_events.py
```

Expected: retrieval quality can be measured before adding more Agent complexity.

---

## Phase 9: Safety, Permissions, and Production Hardening

**Learning Goal:** Learn agent safety as engineering controls, not vague prompt instructions.

**Files:**

- Create: `app/core/errors.py`
- Create: `app/core/security.py`
- Create: `app/services/tool_permission_service.py`
- Create: `tests/test_tool_permissions.py`
- Create: `tests/test_error_responses.py`

- [ ] **Step 1: Add unified error responses**

Every API error should include:

- `code`
- `message`
- `request_id`
- optional `details`

- [ ] **Step 2: Add tool permission model**

Each tool needs:

- name
- description
- read/write classification
- allowed roles
- sensitive input fields
- whether human approval is required

- [ ] **Step 3: Add trace sensitive data controls**

Do not store full prompts, tool inputs, or document text in traces by default when the data is sensitive.

- [ ] **Step 4: Verify**

Run:

```bash
pytest tests/test_tool_permissions.py tests/test_error_responses.py
```

Expected: tools have explicit permission boundaries and API errors are consistent.

---

## Phase 10: Frontend Agent Workbench

**Learning Goal:** Learn how to expose RAG and Agent internals to users without turning the UI into a debugging dump.

**Files:**

- Modify: `frontend/src/views/ChatWorkspace.vue`
- Modify: `frontend/src/components/chat/CitationList.vue`
- Modify: `frontend/src/components/chat/ThinkingPanel.vue`
- Modify: `frontend/src/components/chat/AssetPreview.vue`
- Create: `frontend/src/api/retrieval.ts`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/api/agentTasks.ts`

- [ ] **Step 1: Show retrieval debug panel**

Display:

- query
- mode
- sources
- total hits
- used hits
- dropped counts
- token budget

- [ ] **Step 2: Show citations**

Display citation ID, preview, source metadata, and score.

- [ ] **Step 3: Show agent events**

Display node timeline:

- router
- retriever
- analyzer
- planner
- reviewer

- [ ] **Step 4: Show assets**

Render image assets as previews linked to citations.

- [ ] **Step 5: Verify**

Run:

```bash
cd frontend
npm run build
```

Expected: frontend builds and the workbench can show retrieval and agent trace data.

---

## Recommended Learning Order

Follow this exact order:

1. Retrieval API tests.
2. Embedding provider and pgvector.
3. Hybrid retrieval and rerank.
4. Asset resolution.
5. Chat persistence and streaming.
6. LangGraph workflow.
7. Durable execution and memory.
8. Observability and evaluation.
9. Safety and permissions.
10. Frontend Agent workbench.

Do not jump to LangGraph before vector retrieval, hybrid retrieval, and evaluation exist. A graph wrapped around a weak retrieval layer only makes the system harder to debug.

## Sources To Study While Implementing

- OpenAI Responses API and tool use: study stateful responses, built-in tools, function calling, and remote MCP tool concepts.
- OpenAI Agents SDK: study tools, handoffs, guardrails, streaming, and tracing.
- LangGraph: study durable execution, persistence/checkpointing, interrupts, memory, and deterministic replay.
- LangSmith concepts: study traces, runs, datasets, offline evaluation, and online evaluation.
- LangChain retrieval docs: study contextual compression and reranking, especially cross-encoder rerankers.

## Self-Review

Spec coverage:

- Current retrieval API stabilization is covered in Phase 1.
- RAG production quality is covered in Phases 2 through 4.
- Chat product behavior is covered in Phase 5.
- Agent implementation is covered in Phases 6 and 7.
- Observability, evaluation, and safety are covered in Phases 8 and 9.
- Frontend learning is covered in Phase 10.

Placeholder scan:

- No `TBD`, `TODO`, or undefined "later" task remains.

Type consistency:

- `RetrievalMode` remains chunk-structure mode: `normal` or `parent_child`.
- Future retrieval source strategy is separated from `RetrievalMode` to avoid overloading one field.
- Agent nodes call service/tool boundaries rather than SQL internals.

