from typing import Protocol
from uuid import UUID
from opensearchpy import OpenSearch
from sqlalchemy.orm import Session

from app.rag.lexical_store import search_chunks_by_bm25
from app.models.retrieval_types import ChunkHit


class LexicalRetriever(Protocol):
    """
    lexical retriever 的接口。

    为什么要有这一层：
    - retrieval service 只关心“给我 keyword hits”，不应该知道底层是 OpenSearch 还是 Elasticsearch。
    - 测试时可以传 fake retriever，不需要启动真实搜索引擎。
    - 后续如果你从 OpenSearch 换成 Elasticsearch / ParadeDB / Vespa，上层 pipeline 不用改。
    """

    def search(
        self,
        db: Session,
        *,
        query: str,
        chunk_type: str,
        document_ids: list[UUID] | None,
        top_k: int,
    ) -> list[ChunkHit]:
        ...


class OpenSearchBM25Retriever:
    """
    OpenSearch BM25 retriever。

    这一层只做依赖绑定：
    - client：OpenSearch 连接
    - index_name：chunk 索引名

    真正的 query body 和结果转换仍然放在 lexical_store.py。
    """

    def __init__(
        self,
        *,
        client: OpenSearch,
        index_name: str,
    ) -> None:
        self.client = client
        self.index_name = index_name

    def search(
        self,
        db: Session,
        *,
        query: str,
        chunk_type: str,
        document_ids: list[UUID] | None,
        top_k: int,
    ) -> list[ChunkHit]:
        return search_chunks_by_bm25(
            db=db,
            client=self.client,
            index_name=self.index_name,
            query=query,
            chunk_type=chunk_type,
            document_ids=document_ids,
            top_k=top_k,
        )