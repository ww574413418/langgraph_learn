from opensearchpy import OpenSearch

from app.core.config import settings
from app.db.session import SessionLocal
from app.rag.lexical_retriever import OpenSearchBM25Retriever


def main() -> None:
    client = OpenSearch(hosts=[settings.opensearch_url])
    retriever = OpenSearchBM25Retriever(
        client=client,
        index_name=settings.opensearch_chunks_index,
    )

    db = SessionLocal()

    try:
        hits = retriever.search(
            db=db,
            query="机器人无法充电",
            chunk_type="child",
            document_ids=None,
            top_k=5,
        )

        print(f"hits: {len(hits)}")

        for hit in hits:
            print(
                {
                    "chunk_id": str(hit.chunk.id),
                    "chunk_type": hit.chunk.chunk_type,
                    "score": hit.score,
                    "rank": hit.rank,
                    "preview": hit.chunk.content[:100],
                }
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()