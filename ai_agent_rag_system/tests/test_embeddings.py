from app.rag.embeddings import (
    DeterministicEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from app.core.config import settings


def test_embedding_dimensions_are_fixed_to_1024_for_pgvector_schema() -> None:
    """
    生产约束测试：

    当前阶段我们选择固定 1024 维 embedding。
    pgvector 列会迁移为 vector(1024)，所以应用配置也必须保持 1024。

    如果这里被改成 8 / 1536 / 3072，但没有同步数据库迁移，
    向量写入和向量检索都会在运行时失败。
    """
    assert settings.embedding_dimensions == 1024


def test_deterministic_embedding_provider_returns_expected_dimensions() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    embedding = provider.embed_query("机器人无法充电")

    assert len(embedding) == 8
    assert all(isinstance(value, float) for value in embedding)


def test_deterministic_embedding_provider_returns_same_vector_for_same_text() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    first = provider.embed_query("机器人无法充电")
    second = provider.embed_query("机器人无法充电")

    assert first == second


def test_deterministic_embedding_provider_returns_different_vectors_for_different_text() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    first = provider.embed_query("机器人无法充电")
    second = provider.embed_query("机器人无法回充")

    assert first != second


def test_deterministic_embedding_provider_embeds_documents_in_order() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    texts = ["机器人无法充电", "机器人无法回充"]
    embeddings = provider.embed_documents(texts)

    assert len(embeddings) == 2
    assert embeddings[0] == provider.embed_query(texts[0])
    assert embeddings[1] == provider.embed_query(texts[1])


def test_deterministic_embedding_provider_rejects_empty_text() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    try:
        provider.embed_query("   ")
    except ValueError as exc:
        assert str(exc) == "Embedding text must not be empty"
    else:
        raise AssertionError("Expected ValueError")


def test_openai_compatible_embedding_provider_requests_configured_dimensions() -> None:
    """
    OpenAI-compatible embedding 模型有些原生维度很大，例如 4096。

    如果平台支持 dimensions 参数，我们应该在请求时显式传入项目配置的维度。
    当前数据库是 vector(1024)，所以 provider 请求模型时也要要求输出 1024 维。
    """

    class FakeEmbeddingItem:
        def __init__(self, embedding: list[float]) -> None:
            self.embedding = embedding

    class FakeEmbeddingResponse:
        def __init__(self, embeddings: list[list[float]]) -> None:
            self.data = [FakeEmbeddingItem(embedding) for embedding in embeddings]

    class FakeEmbeddingsResource:
        def __init__(self) -> None:
            self.last_request: dict | None = None

        def create(self, **kwargs) -> FakeEmbeddingResponse:
            self.last_request = kwargs

            input_texts = kwargs["input"]
            dimensions = kwargs["dimensions"]

            return FakeEmbeddingResponse(
                embeddings=[
                    [0.1] * dimensions
                    for _text in input_texts
                ]
            )

    class FakeClient:
        def __init__(self) -> None:
            self.embeddings = FakeEmbeddingsResource()

    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        base_url="https://example.com/v1",
        model_name="test-embedding-model",
        dimensions=1024,
    )
    fake_client = FakeClient()
    provider.client = fake_client

    embedding = provider.embed_query("机器人无法充电")

    assert len(embedding) == 1024
    assert fake_client.embeddings.last_request == {
        "model": "test-embedding-model",
        "input": ["机器人无法充电"],
        "dimensions": 1024,
    }
