# app/rag/lexical_store.py

from uuid import UUID

from opensearchpy import OpenSearch
from sqlalchemy.orm import Session
from app.models.document_chunk import DocumentChunk
from app.models.retrieval_types import ChunkHit


def search_chunks_by_bm25(
    db: Session,
    client: OpenSearch,
    *,
    index_name: str,
    query: str,
    chunk_type: str,
    document_ids: list[UUID] | None = None,
    top_k: int = 20,
) -> list[ChunkHit]:
    """
    BM25 lexical retrieval.

    设计思路：
    - OpenSearch 负责“召回和排序”，因为 BM25、分词、字段权重是搜索引擎擅长的事。
    - Postgres 仍然是 source of truth，所以 OpenSearch 返回 chunk_id 后，再回数据库拿 DocumentChunk。
    - 上层 retrieval pipeline 只认识 ChunkHit，不关心底层是 OpenSearch、pgvector 还是别的后端。
    """

    normalized_query = query.strip()
    if not normalized_query:
        return []

    # document_ids=[] 表示“明确限制到空文档集合”。
    # 这里必须直接返回，不能省略过滤条件，否则会误查全库。
    if document_ids == []:
        return []

    filters: list[dict] = [{"term": {"chunk_type": chunk_type}}]

    if document_ids is not None:
        filters.append(
            {"terms": {"document_id": [str(document_id) for document_id in document_ids]}}
        )

    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": normalized_query,
                            # 字段权重：正文最重要，标题次之，文件名只作为弱信号。
                            "fields": ["content^3", "section_title^2", "filename^1.2"],
                            "type": "best_fields",
                            "operator": "or",
                        }
                    }
                ],
                # filter 不参与打分，只做硬约束；这是生产检索里必须区分的点。
                "filter": filters,
            }
        },
    }

    response = client.search(index=index_name, body=body)
    search_hits = response["hits"]["hits"]

    chunk_ids = [UUID(item["_source"]["chunk_id"]) for item in search_hits]
    if not chunk_ids:
        return []

    chunks_by_id = {
        chunk.id: chunk
        for chunk in db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
    }

    hits: list[ChunkHit] = []

    for rank, item in enumerate(search_hits, start=1):
        chunk_id = UUID(item["_source"]["chunk_id"])
        chunk = chunks_by_id.get(chunk_id)

        # OpenSearch 和数据库可能短暂不一致。生产上不要因为一条脏索引打断整个查询。
        if chunk is None:
            continue

        hits.append(
            ChunkHit(
                chunk=chunk,
                score=float(item["_score"]),
                raw_score=float(item["_score"]),
                normalized_score=None,
                rank=rank,
                retrieval_source="bm25",
                extra_metadata={
                    "backend": "opensearch",
                    "index": index_name,
                },
            )
        )

    return hits