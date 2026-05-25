'''
RAG 检索链路的统一数据结构。

用于连接候选召回、父子 chunk 回填、rerank 和上下文组装。
不是最终直接传给 LLM 的 prompt 格式。
'''

from dataclasses import dataclass
from typing import Literal
from app.models.document_chunk import DocumentChunk


RetrievalSource = Literal["vector", "keyword", "hybrid", "rerank", "manual"]
RetrievalMode = Literal["normal", "parent_child"]


@dataclass
class ChunkHit:
    chunk: DocumentChunk
    score: float | None = None
    retrieval_source: RetrievalSource = "manual"


@dataclass
class ContextCandidate:
    context_chunk: DocumentChunk
    citation_chunk: DocumentChunk
    score: float | None = None
    retrieval_mode: RetrievalMode = "normal"
    retrieval_source: RetrievalSource = "manual"