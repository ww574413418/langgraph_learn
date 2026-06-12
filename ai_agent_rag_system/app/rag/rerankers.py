from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from app.models.retrieval_types import ContextCandidate
import os
import requests
from collections.abc import Callable

@dataclass
class RerankItem:
    """
    表示一个等待 rerank 的候选项。

    这里故意不直接依赖 DocumentChunk / ContextCandidate，
    因为 reranker 的职责只是判断 query 和 text 的相关性。

    字段说明：
    - item_id: 候选项的稳定 ID，通常用 citation_chunk.id
    - text: 给 reranker 判断相关性的文本
      normal 模式：normal chunk content
      parent_child 模式：child chunk content
    - original_score: 召回阶段的分数，例如 BM25 / vector / hybrid 分数
    - original_rank: 召回阶段的排名
    - metadata: 扩展信息，方便调试和 trace，不参与排序逻辑
    """
    item_id: str
    text: str
    original_score: float | None = None
    original_rank: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RerankResult:
    """
    表示 reranker 对单个候选项的打分结果。

    字段说明：
    - item_id: 对应 RerankItem.item_id
    - score: reranker 给出的相关性分数，越大越相关
    - rank: rerank 后的新排名，从 1 开始
    - raw_score: 模型原始分数。第一版可以和 score 一样。
    - metadata: 记录 reranker 名称、原始 rank、原始 score 等调试信息
    """
    item_id: str
    score: float
    rank: int
    raw_score: float | None = None
    metadata: dict = field(default_factory=dict)


class BaseReranker(ABC):
    """
    reranker 抽象接口。

    为什么要抽象：
    - 第一版可以用 FakeReranker 写测试。
    - 后续可以换成真实 Cross Encoder / Cohere / BGE reranker。
    - retrieval pipeline 不需要知道具体模型怎么调用。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        reranker 名称，用于 trace 和 debug。

        例如：
        - fake-reranker
        - bge-reranker
        - cohere-rerank
        """
        raise NotImplementedError

    @abstractmethod
    def rerank(
        self,
        *,
        query: str,
        items: list[RerankItem],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """
        对候选文本进行重排序。

        参数：
        - query: 用户问题
        - items: 召回阶段得到的候选项
        - top_k: 如果传入，只返回 rerank 后前 top_k 条

        返回：
        - 按 rerank score 从高到低排序的 RerankResult 列表
        """
        raise NotImplementedError


class FakeReranker(BaseReranker):
    """
    测试用 reranker。

    设计目标：
    - 不调用真实模型。
    - 结果稳定。
    - 可以通过 item_id -> score 控制排序结果。

    这样你可以精准测试：
    - rerank 后顺序是否变化
    - rank 是否重新生成
    - top_k 是否生效
    - metadata 是否保留
    """

    def __init__(self, scores_by_item_id: dict[str, float]) -> None:
        self.scores_by_item_id = scores_by_item_id
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "fake-reranker"

    def rerank(
        self,
        *,
        query: str,
        items: list[RerankItem],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        normalized_query = query.strip()

        # 记录调用参数，方便测试确认 pipeline 是否真的调用了 reranker。
        self.calls.append(
            {
                "query": normalized_query,
                "item_count": len(items),
                "top_k": top_k,
            }
        )

        if not normalized_query:
            return []

        results: list[RerankResult] = []

        for item in items:
            # 没有显式配置分数的 item 给 0 分。
            # 这样 fake reranker 不会因为测试数据不完整而报错。
            score = self.scores_by_item_id.get(item.item_id, 0.0)

            results.append(
                RerankResult(
                    item_id=item.item_id,
                    score=score,
                    raw_score=score,
                    rank=0,  # 先占位，排序后再统一写 rank
                    metadata={
                        "reranker": self.name,
                        "original_score": item.original_score,
                        "original_rank": item.original_rank,
                    },
                )
            )

        results.sort(
            key=lambda result: (
                result.score,
                result.item_id,  # tie-breaker，保证同分时排序稳定
            ),
            reverse=True,
        )

        if top_k is not None:
            results = results[:top_k]

        for index, result in enumerate(results, start=1):
            result.rank = index

        return results


def build_rerank_items_from_candidates(
    candidates: list[ContextCandidate],
) -> list[RerankItem]:
    """
    把 retrieval pipeline 里的 ContextCandidate 转成 reranker 输入。

    核心设计：
    - rerank 永远看 citation_chunk.content
    - normal 模式：
        context_chunk = normal chunk
        citation_chunk = normal chunk
      所以 rerank 的 text 是 normal chunk 内容。
    - parent_child 模式：
        context_chunk = parent chunk
        citation_chunk = child chunk
      所以 rerank 的 text 是 child chunk 内容。

    为什么不用 context_chunk.content？
    - parent chunk 更长，适合提供上下文。
    - child chunk 更短，适合判断和 query 的相关性。
    """
    items: list[RerankItem] = []

    for candidate in candidates:
        citation_chunk = candidate.citation_chunk

        items.append(
            RerankItem(
                item_id=str(citation_chunk.id),
                text=citation_chunk.content,
                original_score=candidate.score,
                original_rank=candidate.rank,
                metadata={
                    "retrieval_mode": candidate.retrieval_mode,
                    "retrieval_source": candidate.retrieval_source,
                    "context_chunk_id": str(candidate.context_chunk.id),
                    "citation_chunk_id": str(candidate.citation_chunk.id),
                    "chunk_type": candidate.citation_chunk.chunk_type,
                },
            )
        )

    return items


def apply_rerank_results_to_candidates(
    candidates: list[ContextCandidate],
    rerank_results: list[RerankResult],
) -> list[ContextCandidate]:
    """
    把 rerank 结果应用回 ContextCandidate。

    输入：
    - candidates: 原始 retrieval candidates
    - rerank_results: reranker 输出的新排序和新分数

    输出：
    - 按 rerank rank 排序后的 candidates
    - candidate.score 更新为 rerank score
    - candidate.rank 更新为 rerank rank
    - candidate.retrieval_source 更新为 "rerank"
    - candidate.extra_metadata 里保留 rerank 前的分数和来源信息

    注意：
    这里不修改 context_chunk / citation_chunk 的关系。
    parent_child 模式下，仍然是：
    - context_chunk = parent
    - citation_chunk = child
    """

    # 先按 citation_chunk.id 建索引。
    # 因为我们前面用 citation_chunk.id 作为 RerankItem.item_id。
    candidates_by_item_id = {
        str(candidate.citation_chunk.id): candidate
        for candidate in candidates
    }

    reranked_candidates: list[ContextCandidate] = []

    for result in rerank_results:
        candidate = candidates_by_item_id.get(result.item_id)

        # best-effort：如果 reranker 返回了未知 item_id，跳过。
        # 这样真实模型或外部服务异常返回多余 id 时，不会让整个检索请求失败。
        if candidate is None:
            continue

        previous_score = candidate.score
        previous_rank = candidate.rank
        previous_source = candidate.retrieval_source

        candidate.score = result.score
        candidate.rank = result.rank
        candidate.retrieval_source = "rerank"

        candidate.extra_metadata = {
            **candidate.extra_metadata,
            "rerank": {
                "score": result.score,
                "rank": result.rank,
                "raw_score": result.raw_score,
                "metadata": result.metadata,
            },
            "before_rerank": {
                "score": previous_score,
                "rank": previous_rank,
                "retrieval_source": previous_source,
            },
        }

        reranked_candidates.append(candidate)

    return reranked_candidates



SiliconFlowPostFn = Callable[[dict], dict]

class SiliconFlowReranker(BaseReranker):
    """
    SiliconFlow 专用 reranker。

    它调用的是 /v1/rerank 专用接口，不是 Chat Completions。
    所以这里不需要 prompt，也不需要解析 LLM JSON。
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "BAAI/bge-reranker-v2-m3",
        base_url: str = "https://api.siliconflow.cn",
        timeout_seconds: float = 30.0,
        post_fn: SiliconFlowPostFn | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.post_fn = post_fn

    @property
    def name(self) -> str:
        return "siliconflow-reranker"

    def rerank(
        self,
        *,
        query: str,
        items: list[RerankItem],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        if not items:
            return []

        top_n = top_k if top_k is not None else len(items)
        top_n = min(top_n, len(items))

        payload = {
            "model": self.model,
            "query": normalized_query,
            "documents": [item.text for item in items],
            "return_documents": False,
            "top_n": top_n,
        }

        response_data = self._post(payload)

        return self._parse_response(
            response_data=response_data,
            items=items,
        )

    def _post(self, payload: dict) -> dict:
        """
        发起 SiliconFlow rerank 请求。

        测试时传 post_fn，不会真的请求网络。
        生产时不传 post_fn，使用 requests.post。
        """
        if self.post_fn is not None:
            return self.post_fn(payload)

        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY is required")

        response = requests.post(
            f"{self.base_url}/v1/rerank",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {"message": response.text}

            raise RuntimeError(
                f"SiliconFlow rerank failed: "
                f"status={response.status_code}, error={error_data}"
            )

        return response.json()

    def _parse_response(
        self,
        *,
        response_data: dict,
        items: list[RerankItem],
    ) -> list[RerankResult]:
        """
        把 SiliconFlow 响应转成统一 RerankResult。

        SiliconFlow 返回的是 documents 的下标 index。
        所以必须用 index 映射回原始 RerankItem.item_id。
        """
        raw_results = response_data.get("results", [])

        results: list[RerankResult] = []

        for rank, raw_item in enumerate(raw_results, start=1):
            index = raw_item["index"]

            if index < 0 or index >= len(items):
                raise ValueError(f"Invalid rerank result index: {index}")

            item = items[index]
            score = float(raw_item["relevance_score"])

            results.append(
                RerankResult(
                    item_id=item.item_id,
                    score=score,
                    raw_score=score,
                    rank=rank,
                    metadata={
                        "reranker": self.name,
                        "model": self.model,
                        "provider": "siliconflow",
                        "provider_index": index,
                        "provider_id": response_data.get("id"),
                        "meta": response_data.get("meta", {}),
                    },
                )
            )

        return results
