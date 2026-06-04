from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.lexical_store import search_chunks_by_bm25


class FakeOpenSearch:
    """
    单元测试不要依赖真实 OpenSearch。

    这里 fake 的目的不是模拟搜索引擎算法，而是验证：
    - 我们发给 OpenSearch 的 query body 是否正确
    - OpenSearch 返回 chunk_id 后，代码是否能回数据库拿到真实 DocumentChunk
    - rank / score / retrieval_source 是否按 contract 输出
    """

    def __init__(self, hits: list[dict]) -> None:
        self.hits = hits
        self.calls: list[dict] = []

    def search(self, *, index: str, body: dict) -> dict:
        self.calls.append({"index": index, "body": body})
        return {"hits": {"hits": self.hits}}


class FailingOpenSearch:
    def search(self, *, index: str, body: dict) -> dict:
        raise AssertionError("OpenSearch should not be called")


def create_test_session() -> Session:
    engine = create_engine(settings.database_url)
    return Session(engine)


def create_test_document(db: Session) -> Document:
    marker = str(uuid4())

    kb = KnowledgeBase(
        name=f"bm25-test-kb-{marker}",
        description="bm25 retrieval test",
        domain="test",
        status="active",
        extra_metadata={"test_marker": marker},
        retrieval_config={},
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    document = Document(
        knowledge_base_id=kb.id,
        filename=f"bm25-test-{marker}.txt",
        file_type="txt",
        file_path=f"data/bm25-test-{marker}.txt",
        file_hash=f"bm25-test-hash-{marker}",
        status="indexed",
        extra_metadata={"test_marker": marker},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def create_chunk(
    db: Session,
    *,
    document_id,
    chunk_type: str,
    content: str,
    chunk_index: int,
) -> DocumentChunk:
    chunk = DocumentChunk(
        id=uuid4(),
        document_id=document_id,
        chunk_type=chunk_type,
        chunk_index=chunk_index,
        content=content,
        content_hash=f"bm25-test-chunk-hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        start_char=0,
        end_char=len(content),
        extra_metadata={"file_type": "txt"},
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def cleanup_test_document(db: Session, document: Document) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    knowledge_base_id = document.knowledge_base_id
    db.query(Document).filter(Document.id == document.id).delete()
    db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).delete()
    db.commit()


def test_search_chunks_by_bm25_returns_ranked_chunk_hits() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        best = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="机器人无法充电，需要检查充电底座。",
            chunk_index=0,
        )

        weaker = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="机器人清洁维护说明。",
            chunk_index=1,
        )

        client = FakeOpenSearch(
            hits=[
                {"_score": 12.5, "_source": {"chunk_id": str(best.id)}},
                {"_score": 3.2, "_source": {"chunk_id": str(weaker.id)}},
            ]
        )

        hits = search_chunks_by_bm25(
            db=db,
            client=client,
            index_name="rag-chunks-test",
            query="机器人 充电",
            chunk_type="normal",
            document_ids=[document.id],
            top_k=20,
        )

        assert [hit.chunk.id for hit in hits] == [best.id, weaker.id]
        assert hits[0].rank == 1
        assert hits[0].score == 12.5
        assert hits[0].retrieval_source == "bm25"

        body = client.calls[0]["body"]
        assert body["size"] == 20
        assert {"term": {"chunk_type": "normal"}} in body["query"]["bool"]["filter"]
        assert {
            "terms": {"document_id": [str(document.id)]}
        } in body["query"]["bool"]["filter"]

    finally:
        cleanup_test_document(db, document)
        db.close()


def test_search_chunks_by_bm25_empty_document_scope_returns_no_hits() -> None:
    db = create_test_session()

    hits = search_chunks_by_bm25(
        db=db,
        client=FailingOpenSearch(),
        index_name="rag-chunks-test",
        query="机器人",
        chunk_type="normal",
        document_ids=[],
        top_k=20,
    )

    assert hits == []
    db.close()


def test_search_chunks_by_bm25_skips_stale_search_index_hits() -> None:
    db = create_test_session()
    missing_chunk_id = uuid4()

    client = FakeOpenSearch(
        hits=[
            {"_score": 9.0, "_source": {"chunk_id": str(missing_chunk_id)}},
        ]
    )

    hits = search_chunks_by_bm25(
        db=db,
        client=client,
        index_name="rag-chunks-test",
        query="机器人",
        chunk_type="normal",
        document_ids=None,
        top_k=20,
    )

    assert hits == []
    db.close()