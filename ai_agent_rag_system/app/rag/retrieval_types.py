from dataclasses import dataclass, field
from typing import Literal

from app.models.document_chunk import DocumentChunk


RetrievalSource = Literal[
    "vector",
    "keyword",
    "bm25",
    "pg_trgm",
    "full_text",
    "hybrid",
    "rerank",
    "manual",
]

RetrievalMode = Literal["normal", "parent_child"]


@dataclass
class ChunkHit:
    chunk: DocumentChunk
    score: float | None = None
    rank: int | None = None
    retrieval_source: RetrievalSource = "manual"
    raw_score: float | None = None
    normalized_score: float | None = None
    extra_metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalTrace:
    query: str
    mode: RetrievalMode
    sources: list[RetrievalSource]
    total_hits: int
    used_hits: int
    source_hit_counts: dict[str, int] = field(default_factory=dict)
    dropped_hit_counts: dict[str, int] = field(default_factory=dict)
    extra_metadata: dict = field(default_factory=dict)


@dataclass
class ContextCandidate:
    context_chunk: DocumentChunk
    citation_chunk: DocumentChunk
    score: float | None = None
    rank: int | None = None
    retrieval_mode: RetrievalMode = "normal"
    retrieval_source: RetrievalSource = "manual"
    extra_metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    candidates: list[ContextCandidate]
    trace: RetrievalTrace