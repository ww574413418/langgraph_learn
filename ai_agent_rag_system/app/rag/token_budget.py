from dataclasses import dataclass, field
from typing import Literal
from app.models.retrieval_types import ContextCandidate, RetrievalMode

TaskType = Literal["qa", "summarize", "analysis", "code", "extract"]

@dataclass(frozen=True)
class TokenBudgetRequest:
    '''
    一次 RAG 请求的预算计算输入。
    '''

    model_name: str | None = None
    model_context_window: int | None = None
    task_type: TaskType = "qa"
    retrieval_mode: RetrievalMode = "parent_child"
    candidate_count: int = 0
    document_types: tuple[str, ...] = field(default_factory=tuple)

    user_query_tokens: int = 200
    history_tokens: int = 0
    system_prompt_tokens: int = 800
    reserved_answer_tokens: int | None = None

    max_context_token_cap: int = 24_000
    max_chunk_token_cap: int = 2_400

@dataclass(frozen=True)
class TokenBudgetPlan:
    """
    预算策略计算后的结果，后续会传给 assemble_context()。
    """

    max_context_tokens: int
    max_chunk_tokens: int
    citation_preview_tokens: int

    model_context_window: int
    available_prompt_tokens: int
    reserved_answer_tokens: int

DEFAULT_MODEL_CONTEXT_WINDOW = 8192

MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_000_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    "o3": 200_000,
    "o4-mini": 200_000,
}


def resolve_model_context_window(
    model_name: str | None,
    model_context_window: int | None,
) -> int:
    """
    决定本次请求可用的模型上下文窗口。

    优先级：
    1. 调用方显式传入 model_context_window。
    2. 根据 model_name 匹配已知模型。
    3. 使用默认窗口。
    """

    if model_context_window is not None:
        return max(1024, model_context_window)

    if model_name:
        normalized_name = model_name.lower()

        for known_model, context_window in MODEL_CONTEXT_WINDOWS.items():
            if known_model in normalized_name:
                return context_window

    return DEFAULT_MODEL_CONTEXT_WINDOW


def default_answer_tokens(task_type: TaskType) -> int:
    """
    根据任务类型预留回答空间。

    这个值不会直接进入 RAG context。
    它是从模型总窗口里扣掉的，避免上下文塞太满导致模型没空间回答。
    """

    if task_type == "summarize":
        return 1800

    if task_type == "analysis":
        return 1600

    if task_type == "code":
        return 1400

    if task_type == "extract":
        return 900

    return 1200


def calculate_available_prompt_tokens(
    request: TokenBudgetRequest,
) -> tuple[int, int, int]:
    """
    计算本次请求除 RAG context 外已经占用或预留的 token。

    返回：
    - model_context_window
    - reserved_answer_tokens
    - available_prompt_tokens
    """

    model_context_window = resolve_model_context_window(
        model_name=request.model_name,
        model_context_window=request.model_context_window,
    )

    reserved_answer_tokens = (
        request.reserved_answer_tokens
        if request.reserved_answer_tokens is not None
        else default_answer_tokens(request.task_type)
    )

    available_prompt_tokens = max(
        0,
        model_context_window
        - request.system_prompt_tokens
        - request.user_query_tokens
        - request.history_tokens
        - reserved_answer_tokens,
    )

    return model_context_window, reserved_answer_tokens, available_prompt_tokens

def has_code_like_document(document_types: tuple[str, ...]) -> bool:
    """
    判断候选文档类型里是否包含代码类内容。
    """

    return any(
        document_type in {"code", "py", "js", "ts", "tsx", "java", "go"}
        for document_type in document_types
    )


def resolve_context_fraction(
    task_type: TaskType,
    retrieval_mode: RetrievalMode,
    document_types: tuple[str, ...],
) -> float:
    """
    决定 available_prompt_tokens 中有多少比例可以给 RAG context。
    """

    fraction_by_task: dict[TaskType, float] = {
        "qa": 0.60,
        "summarize": 0.70,
        "analysis": 0.66,
        "code": 0.70,
        "extract": 0.52,
    }

    fraction = fraction_by_task[task_type]

    if retrieval_mode == "parent_child":
        fraction += 0.06

    if has_code_like_document(document_types):
        fraction += 0.06
    elif "md" in document_types:
        fraction += 0.03

    return min(fraction, 0.82)


def clamp(value: int, *, minimum: int, maximum: int) -> int:
    """
    把 value 限制在 minimum 和 maximum 之间。
    """

    if maximum < minimum:
        return maximum

    return max(minimum, min(value, maximum))


def resolve_max_context_tokens(
    request: TokenBudgetRequest,
    available_prompt_tokens: int,
) -> int:
    """
    从 available_prompt_tokens 中切出 RAG context 总预算。
    """

    context_fraction = resolve_context_fraction(
        task_type=request.task_type,
        retrieval_mode=request.retrieval_mode,
        document_types=request.document_types,
    )

    raw_context_tokens = int(available_prompt_tokens * context_fraction)

    max_context_tokens = clamp(
        raw_context_tokens,
        minimum=0 if available_prompt_tokens == 0 else min(512, available_prompt_tokens),
        maximum=min(available_prompt_tokens, request.max_context_token_cap),
    )

    return max_context_tokens

def resolve_max_chunk_tokens(
    *,
    max_context_tokens: int,
    candidate_count: int,
    task_type: TaskType,
    retrieval_mode: RetrievalMode,
    document_types: tuple[str, ...],
    max_chunk_token_cap: int,
) -> int:
    """
    决定单个 context candidate 最多放多少 token。
    """

    if max_context_tokens <= 0:
        return 0

    effective_candidates = max(1, min(candidate_count or 1, 8))
    per_candidate_budget = max_context_tokens // effective_candidates

    minimum = 260
    maximum = 900

    if retrieval_mode == "parent_child":
        minimum = 500
        maximum = 1600

    if has_code_like_document(document_types) or task_type == "code":
        minimum = max(minimum, 700)
        maximum = max(maximum, 2200)

    if task_type == "summarize":
        maximum = max(maximum, 2000)

    maximum = min(maximum, max_chunk_token_cap, max_context_tokens)
    minimum = min(minimum, maximum)

    return clamp(
        per_candidate_budget - 24,
        minimum=minimum,
        maximum=maximum,
    )

def resolve_citation_preview_tokens(
    *,
    task_type: TaskType,
    document_types: tuple[str, ...],
    max_chunk_tokens: int,
) -> int:
    """
    决定 citation preview 的 token 长度。
    """

    if task_type == "extract":
        preview_tokens = 60
    elif task_type in {"analysis", "code"} or has_code_like_document(document_types):
        preview_tokens = 120
    elif task_type == "summarize":
        preview_tokens = 100
    else:
        preview_tokens = 80

    return min(
        preview_tokens,
        max(20, max_chunk_tokens // 2),
    )

def build_dynamic_token_budget(
    request: TokenBudgetRequest,
) -> TokenBudgetPlan:
    """
    根据一次 RAG 请求信息，生成 Context Assembly 所需的动态预算。
    """

    (
        model_context_window,
        reserved_answer_tokens,
        available_prompt_tokens,
    ) = calculate_available_prompt_tokens(request)

    max_context_tokens = resolve_max_context_tokens(
        request=request,
        available_prompt_tokens=available_prompt_tokens,
    )

    max_chunk_tokens = resolve_max_chunk_tokens(
        max_context_tokens=max_context_tokens,
        candidate_count=request.candidate_count,
        task_type=request.task_type,
        retrieval_mode=request.retrieval_mode,
        document_types=request.document_types,
        max_chunk_token_cap=request.max_chunk_token_cap,
    )

    citation_preview_tokens = resolve_citation_preview_tokens(
        task_type=request.task_type,
        document_types=request.document_types,
        max_chunk_tokens=max_chunk_tokens,
    )

    return TokenBudgetPlan(
        max_context_tokens=max_context_tokens,
        max_chunk_tokens=max_chunk_tokens,
        citation_preview_tokens=citation_preview_tokens,
        model_context_window=model_context_window,
        available_prompt_tokens=available_prompt_tokens,
        reserved_answer_tokens=reserved_answer_tokens,
    )

def infer_retrieval_mode(
    candidates: list[ContextCandidate],
) -> RetrievalMode:
    """
    从候选列表推断本次上下文组装使用的 retrieval mode。
    """

    if any(candidate.retrieval_mode == "parent_child" for candidate in candidates):
        return "parent_child"

    return "normal"


def looks_like_code(text: str) -> bool:
    """
    粗略判断文本是否像代码。

    这不是严格语言识别，只用于预算策略：
    代码类上下文应该给更大的 chunk window。
    """

    code_markers = (
        "```",
        "def ",
        "class ",
        "function ",
        "=>",
        "import ",
        "return ",
    )

    return any(marker in text for marker in code_markers)


def infer_document_types(
    candidates: list[ContextCandidate],
) -> tuple[str, ...]:
    """
    从候选 chunk metadata 和文本内容推断文档类型。
    """

    document_types: set[str] = set()

    for candidate in candidates:
        for chunk in (candidate.context_chunk, candidate.citation_chunk):
            metadata = chunk.extra_metadata or {}
            file_type = metadata.get("file_type")

            if isinstance(file_type, str) and file_type:
                document_types.add(file_type.lower())

        if looks_like_code(candidate.context_chunk.content) or looks_like_code(
            candidate.citation_chunk.content
        ):
            document_types.add("code")

    return tuple(sorted(document_types))


def build_token_budget_request_from_candidates(
    candidates: list[ContextCandidate],
    *,
    model_name: str | None = None,
    model_context_window: int | None = None,
    task_type: TaskType = "qa",
    retrieval_mode: RetrievalMode | None = None,
    user_query_tokens: int = 200,
    history_tokens: int = 0,
    system_prompt_tokens: int = 800,
    reserved_answer_tokens: int | None = None,
    max_context_token_cap: int = 24_000,
    max_chunk_token_cap: int = 2_400,
) -> TokenBudgetRequest:
    """
    从 ContextCandidate 列表构造动态预算请求。
    """

    inferred_mode = retrieval_mode or infer_retrieval_mode(candidates)

    return TokenBudgetRequest(
        model_name=model_name,
        model_context_window=model_context_window,
        task_type=task_type,
        retrieval_mode=inferred_mode,
        candidate_count=len(candidates),
        document_types=infer_document_types(candidates),
        user_query_tokens=user_query_tokens,
        history_tokens=history_tokens,
        system_prompt_tokens=system_prompt_tokens,
        reserved_answer_tokens=reserved_answer_tokens,
        max_context_token_cap=max_context_token_cap,
        max_chunk_token_cap=max_chunk_token_cap,
    )