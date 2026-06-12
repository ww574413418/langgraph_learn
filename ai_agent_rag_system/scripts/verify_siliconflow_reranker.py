from app.core.config import settings
from app.rag.rerankers import RerankItem, SiliconFlowReranker


def main() -> None:
    reranker = SiliconFlowReranker(
        api_key=settings.reranker_api_key,
        base_url=settings.reranker_base_url,
        model=settings.reranker_model,
    )

    print("base_url:", settings.reranker_base_url)
    print("model:", settings.reranker_model)

    items = [
        RerankItem(item_id="doc-apple", text="apple"),
        RerankItem(item_id="doc-banana", text="banana"),
        RerankItem(item_id="doc-fruit", text="fruit"),
        RerankItem(item_id="doc-vegetable", text="vegetable"),
    ]

    results = reranker.rerank(
        query="Apple",
        items=items,
        top_k=4,
    )

    for result in results:
        print(
            {
                "item_id": result.item_id,
                "score": result.score,
                "rank": result.rank,
                "metadata": result.metadata,
            }
        )


if __name__ == "__main__":
    main()