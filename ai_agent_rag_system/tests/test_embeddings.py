from app.rag.embeddings import DeterministicEmbeddingProvider


from app.rag.embeddings import DeterministicEmbeddingProvider


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