from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document
from app.rag.tokenizers import TiktokenTokenCounter
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalCitation,
    RetrievalBudgetPlan,
    RetrievalTraceRead
)
from app.services.context_assembly_service import assemble_context_with_dynamic_budget
from app.services.document_retrieval_service import retrieve_context
from app.core.config import settings
from app.rag.rerankers import BaseReranker, FakeReranker, SiliconFlowReranker
from app.rag.embeddings import EmbeddingProvider, create_embedding_provider
from opensearchpy import OpenSearch
from app.core.config import settings
from app.rag.lexical_retriever import LexicalRetriever, OpenSearchBM25Retriever

def resolve_retrieval_document_ids(
    db: Session,
    request: RetrievalRequest,
) -> list[UUID] | None:
    # 不传 knowledge_base_id：按 document_ids 检索；如果也没传，就是全库检索。
    if request.knowledge_base_id is None:
        return request.document_ids

    # 传了 knowledge_base_id：只检索这个知识库下 status="indexed" 的文档。
    stmt = select(Document.id).where(
        Document.knowledge_base_id == request.knowledge_base_id,
        Document.status == "indexed",
    )
    # 同时传 knowledge_base_id 和 document_ids：取交集，避免越界查到别的知识库文档。
    if request.document_ids:
        stmt = stmt.where(Document.id.in_(request.document_ids))

    return list(db.scalars(stmt).all())

def build_retrieval_response(
    *,
    assembled_context,
    budget_plan,
    trace,
) -> RetrievalResponse:
    '''
    内部对象是 dataclass，API 返回的是 Pydantic schema。不要在 route 里手写转换，放 service 里。
    '''
    return RetrievalResponse(
        context_text=assembled_context.context_text,
        citations=[
            RetrievalCitation(
                citation_id=citation.citation_id,
                document_id=citation.document_id,
                context_chunk_id=citation.context_chunk_id,
                citation_chunk_id=citation.citation_chunk_id,
                retrieval_mode=citation.retrieval_mode,
                retrieval_source=citation.retrieval_source,
                score=citation.score,
                metadata=citation.metadata,
                preview=citation.preview,
            )
            for citation in assembled_context.citations
        ],
        budget_plan=RetrievalBudgetPlan(
            max_context_tokens=budget_plan.max_context_tokens,
            max_chunk_tokens=budget_plan.max_chunk_tokens,
            citation_preview_tokens=budget_plan.citation_preview_tokens,
            model_context_window=budget_plan.model_context_window,
            available_prompt_tokens=budget_plan.available_prompt_tokens,
            reserved_answer_tokens=budget_plan.reserved_answer_tokens,
        ),
        trace=RetrievalTraceRead(
            query=trace.query,
            mode=trace.mode,
            sources=list(trace.sources),
            total_hits=trace.total_hits,
            used_hits=trace.used_hits,
            source_hit_counts=trace.source_hit_counts,
            dropped_hit_counts=trace.dropped_hit_counts,
            extra_metadata=trace.extra_metadata,
        ),
        truncated=assembled_context.truncated,
        total_tokens=assembled_context.total_tokens,
        max_context_tokens=assembled_context.max_context_tokens,
    )

def run_retrieval(
    db: Session,
    request: RetrievalRequest,
) -> RetrievalResponse:
    '''
    request
      -> resolve document_ids
      -> retrieve_context()
      -> candidates + trace
      -> assemble_context_with_dynamic_budget()
      -> context_text + citations + budget_plan
      -> RetrievalResponse
    '''
    document_ids = resolve_retrieval_document_ids(db=db, request=request)

    embedding_provider = build_embedding_provider_for_request(request)
    lexical_retriever = build_lexical_retriever_for_request(request)
    reranker = build_reranker_for_request(request)


    retrieval_result = retrieve_context(
        db=db,
        query=request.query,
        document_ids=document_ids,
        mode=request.mode,
        strategy=request.strategy,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever,
        reranker=reranker,
        top_k=request.top_k,
        retrieval_top_k=request.retrieval_top_k,
        rerank_top_k=request.rerank_top_k,
        context_top_k=request.context_top_k,
    )

    token_counter = TiktokenTokenCounter()

    assembled_context, budget_plan = assemble_context_with_dynamic_budget(
        candidates=retrieval_result.candidates,
        token_counter=token_counter,
        model_name=request.model_name,
        model_context_window=request.model_context_window,
        task_type=request.task_type,
        user_query_tokens=request.user_query_tokens,
        history_tokens=request.history_tokens,
        system_prompt_tokens=request.system_prompt_tokens,
        reserved_answer_tokens=request.reserved_answer_tokens,
    )

    return build_retrieval_response(
        assembled_context=assembled_context,
        budget_plan=budget_plan,
        trace=retrieval_result.trace,
    )

def build_reranker_for_request(
    request: RetrievalRequest,
) -> BaseReranker | None:
    """
    根据 API 请求构造 reranker。

    这里属于 API service 层：
    - 读取 request.rerank_mode
    - 读取 settings
    - 构造具体 provider adapter

    底层 document_retrieval_service.py 仍然只接收 BaseReranker | None。
    """
    if request.rerank_mode == "none":
        return None

    if request.rerank_mode == "fake":
        return FakeReranker(scores_by_item_id={})

    if request.rerank_mode == "siliconflow":
        return SiliconFlowReranker(
            api_key=settings.reranker_api_key,
            base_url=settings.reranker_base_url,
            model=settings.reranker_model,
            timeout_seconds=settings.reranker_timeout_seconds,
        )

    raise ValueError("Invalid rerank mode")

def build_embedding_provider_for_request(
    request: RetrievalRequest,
) -> EmbeddingProvider | None:
    """
    vector / hybrid 需要 query embedding。
    bm25 不需要 embedding provider。
    """
    if request.strategy not in ("vector", "hybrid"):
        return None

    return create_embedding_provider()


def create_opensearch_client() -> OpenSearch:
    http_auth = None

    if settings.opensearch_username and settings.opensearch_password:
        http_auth = (
            settings.opensearch_username,
            settings.opensearch_password,
        )

    return OpenSearch(
        hosts=[settings.opensearch_url],
        http_auth=http_auth,
        timeout=settings.opensearch_timeout_seconds,
    )

def build_lexical_retriever_for_request(
    request: RetrievalRequest,
) -> LexicalRetriever | None:
    """
    bm25 / hybrid 需要 lexical retriever。
    vector 不需要。
    """
    if request.strategy not in ("bm25", "hybrid"):
        return None

    return OpenSearchBM25Retriever(
        client=create_opensearch_client(),
        index_name=settings.opensearch_chunks_index,
    )
