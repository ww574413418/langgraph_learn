from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

RetrievalMode = Literal["normal", "parent_child"]
RetrievalStrategy = Literal["bm25", "vector", "hybrid"]
RerankMode = Literal["none", "fake", "siliconflow"]



class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: RetrievalMode = "parent_child"
    top_k: int = Field(default=5, ge=1, le=50)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=50)
    rerank_top_k: int | None = Field(default=None, ge=1, le=50)
    context_top_k: int | None = Field(default=None, ge=1, le=50)
    strategy: RetrievalStrategy = "bm25"
    knowledge_base_id: UUID | None = None
    document_ids: list[UUID] | None = None
    rerank_mode: RerankMode = "none"
    model_name: str | None = None
    model_context_window: int | None = Field(default=None, ge=1024, le=1_000_000)

    task_type: Literal["qa", "summarize", "analysis", "code", "extract"] = "qa"
    user_query_tokens: int = Field(default=200, ge=0, le=4000)
    history_tokens: int = Field(default=0, ge=0, le=200_000)
    system_prompt_tokens: int = Field(default=800, ge=0, le=20_000)
    reserved_answer_tokens: int | None = Field(default=None, ge=0, le=200_000)

class RetrievalCitation(BaseModel):
    citation_id: str
    document_id: UUID
    context_chunk_id: UUID
    citation_chunk_id: UUID
    retrieval_mode: str
    retrieval_source: str
    score: float | None
    metadata: dict
    preview: str

class RetrievalBudgetPlan(BaseModel):
    max_context_tokens: int
    max_chunk_tokens: int
    citation_preview_tokens: int
    model_context_window: int
    available_prompt_tokens: int
    reserved_answer_tokens: int

class RetrievalTraceRead(BaseModel):
    query: str
    mode: str
    sources: list[str]
    total_hits: int
    used_hits: int
    source_hit_counts: dict[str, int] = Field(default_factory=dict)
    dropped_hit_counts: dict[str, int] = Field(default_factory=dict)
    extra_metadata: dict = Field(default_factory=dict)

class RetrievalResponse(BaseModel):
    context_text: str
    citations: list[RetrievalCitation]
    budget_plan: RetrievalBudgetPlan
    trace: RetrievalTraceRead
    truncated: bool
    total_tokens: int
    max_context_tokens: int
