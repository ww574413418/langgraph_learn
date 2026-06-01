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

    retrieval_result = retrieve_context(
        db=db,
        query=request.query,
        document_ids=document_ids,
        mode=request.mode,
        top_k=request.top_k,
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
