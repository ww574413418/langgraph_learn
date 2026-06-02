from hashlib import sha256
from typing import Protocol
from openai import OpenAI
from app.core.config import settings

class EmbeddingProvider(Protocol):
    """
    Embedding provider 协议。
    业务代码只依赖这个协议，不依赖具体供应商。
    好处：
    - 测试可以用 DeterministicEmbeddingProvider
    - 生产可以用 OpenAICompatibleEmbeddingProvider
    - 以后换供应商，不影响 retrieval / indexing 业务代码
    """

    model_name: str
    dimensions: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...


class DeterministicEmbeddingProvider:
    """
    测试用 embedding provider。

    它不追求语义效果，只保证：
    - 同文本得到同向量
    - 不同文本大概率得到不同向量
    - 不依赖网络
    - 不依赖 API Key
    - 测试结果稳定

    注意：
    这个类不能用于真实 RAG 语义检索。
    """

    model_name = "deterministic-test-embedding"

    def __init__(self, dimensions: int = 8) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")

        self.dimensions = dimensions

    def embed_query(self, text: str) -> list[float]:
        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Embedding text must not be empty")

        return self._hash_text_to_vector(normalized_text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def _hash_text_to_vector(self, text: str) -> list[float]:
        vector: list[float] = []
        seed = text.encode("utf-8")
        counter = 0

        while len(vector) < self.dimensions:
            digest = sha256(seed + str(counter).encode("utf-8")).digest()

            for byte in digest:
                if len(vector) >= self.dimensions:
                    break

                # 映射到 [-1, 1]，模拟真实 embedding 的浮点向量形态。
                value = (byte / 255.0) * 2.0 - 1.0
                vector.append(value)

            counter += 1

        return vector


class OpenAICompatibleEmbeddingProvider:
    """
    OpenAI-compatible embedding provider。
    这个类不绑定 OpenAI 官方平台。
    只要求第三方平台兼容 OpenAI embeddings API。
    常见第三方平台一般会提供：
    - api_key
    - base_url
    - model name
    生产关键点：
    - 不在代码里写死模型名
    - 不在代码里写死 base_url
    - 显式校验 embedding 维度
    - 支持批量 embedding
    - 保留 deterministic provider 给测试
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model_name: str,
        dimensions: int,
        timeout_seconds: float = 30.0,
        batch_size: int = 64,
    ) -> None:
        if not api_key:
            raise ValueError("Embedding API key is required")

        if not base_url:
            raise ValueError("Embedding base URL is required")

        if not model_name:
            raise ValueError("Embedding model name is required")

        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")

        if batch_size <= 0:
            raise ValueError("Embedding batch size must be positive")

        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    def embed_query(self, text: str) -> list[float]:
        """
        查询文本 embedding。

        query 通常是一条用户问题，所以直接复用 embed_documents。
        这样 query 和 document 的校验逻辑完全一致。
        """

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Embedding text must not be empty")

        return self.embed_documents([normalized_text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成文档 embedding。

        为什么要批量？
        - indexing 时一个文档会产生很多 chunk
        - 一条一条调 API 会很慢
        - 批量可以减少网络往返

        注意：
        不同供应商 batch 限制不同，所以 batch_size 应该来自配置。
        """

        normalized_texts = [text.strip() for text in texts]

        if not normalized_texts:
            return []

        if any(not text for text in normalized_texts):
            raise ValueError("Embedding documents must not contain empty text")

        all_embeddings: list[list[float]] = []

        for batch in self._batched(normalized_texts, self.batch_size):
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch,
            )

            batch_embeddings = [item.embedding for item in response.data]

            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding response count does not match input count"
                )

            for embedding in batch_embeddings:
                self._validate_embedding_dimensions(embedding)

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _validate_embedding_dimensions(self, embedding: list[float]) -> None:
        """
        校验向量维度。

        这是生产级 RAG 必须做的检查。

        如果数据库是 vector(1024)，但供应商返回 1536 维：
        - 写入会失败
        - 或者更糟，查询时混用不同向量空间

        所以在 provider 层提前失败，错误更清楚。
        """

        actual_dimensions = len(embedding)

        if actual_dimensions != self.dimensions:
            raise RuntimeError(
                f"Embedding dimension mismatch: "
                f"expected {self.dimensions}, got {actual_dimensions}"
            )

    def _batched(
        self,
        texts: list[str],
        batch_size: int,
    ) -> list[list[str]]:
        """
        把文本列表切成多个 batch。

        这里故意不用复杂生成器，方便你调试和学习。
        数据量非常大时，可以改成 yield。
        """

        batches: list[list[str]] = []

        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batches.append(texts[start:end])

        return batches


def create_embedding_provider() -> EmbeddingProvider:
    """
    根据配置创建 embedding provider。

    当前规则：
    - 如果 embedding_model 是 deterministic-test-embedding，使用测试 provider
    - 否则使用 OpenAI-compatible provider

    好处：
    indexing / retrieval 不需要关心 provider 怎么创建。
    """

    if settings.embedding_model == "deterministic-test-embedding":
        return DeterministicEmbeddingProvider(
            dimensions=settings.embedding_dimensions,
        )

    if settings.embedding_api_key is None:
        raise ValueError("EMBEDDING_API_KEY is required")

    if settings.embedding_base_url is None:
        raise ValueError("EMBEDDING_BASE_URL is required")

    return OpenAICompatibleEmbeddingProvider(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model_name=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        timeout_seconds=settings.embedding_timeout_seconds,
        batch_size=settings.embedding_batch_size,
    )