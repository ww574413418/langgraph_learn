'''
Context assembly service.

负责把 ContextCandidate 列表组装成受 token budget 控制、
可引用、可追踪的上下文结果。

1. 按 score / rerank_score 排序。
2. 按 token budget 选择上下文。
3. 对超长 context_chunk 做可控截断。
4. 为每个上下文生成 citation id。
5. citation 保留 document_id、context_chunk_id、citation_chunk_id、metadata、score。
6. 记录是否发生截断。
7. 保留 used_candidates，供后续 asset resolve 使用。
8. 不调用 LLM。
9. 不查数据库。
10. 不处理图片资产，只保留 placeholder，asset resolve 另做。
'''

from dataclasses import dataclass
from uuid import UUID
from app.rag.retrieval_types import ContextCandidate
from app.rag.tokenizers import TokenCounter

@dataclass
class AssembledCitation:
    """
    表示一次上下文组装产生的引用信息。
    用于 API 响应、前端展示和 prompt 引用编号。
    """
    citation_id:str
    document_id:UUID
    context_chunk_id:UUID
    citation_chunk_id:UUID
    retrieval_mode:str
    retrieval_source:str
    score:float | None
    metadata:dict
    preview:str


@dataclass
class AssembledContext:
    context_text:str
    citations:list[AssembledCitation]
    used_candidates:list[ContextCandidate] # 被放入 context_text 的候选。
    dropped_candidates:list[ContextCandidate] # 因 token budget 不够被丢弃的候选。
    total_tokens:int
    max_context_tokens:int
    truncated:bool # 是否发生过 chunk 截断或候选丢弃。


@dataclass
class CitationWindowOffsets:
    start: int
    end: int

@dataclass
class SelectedContextText:
    text: str
    truncated: bool
    token_count: int

# 统一排序规则,只排序,不截断,不改变内容
def sort_candidates(
    candidates: list[ContextCandidate],
) -> list[ContextCandidate]:
    return sorted(
        candidates,
        key=lambda item: item.score if item.score is not None else float("-inf"),
        reverse=True,
    )


# 用 tokenizer 生成 citation 预览。
def build_preview(
    text: str,
    token_counter: TokenCounter,
    max_preview_tokens: int,
) -> str:
    cleaned_text = text.strip()

    if not cleaned_text:
        return ""

    return token_counter.truncate_text(
        cleaned_text,
        max_tokens=max_preview_tokens,
    )

# 生成 prompt 里的单段上下文格式。
def format_context_block(
    citation_id: str,
    content: str,
) -> str:
    return f"[{citation_id}]\n{content.strip()}"


# 从 ContextCandidate 生成结构化 citation。
def build_citation(
    citation_id: str,
    candidate: ContextCandidate,
    preview: str,
) -> AssembledCitation:
    return AssembledCitation(
        citation_id=citation_id,
        document_id=candidate.context_chunk.document_id,
        context_chunk_id=candidate.context_chunk.id,
        citation_chunk_id=candidate.citation_chunk.id,
        retrieval_mode=candidate.retrieval_mode,
        retrieval_source=candidate.retrieval_source,
        score=candidate.score,
        metadata=candidate.citation_chunk.extra_metadata or {},
        preview=preview,
    )

# 计算 citation_chunk 在 context_chunk.content 中的相对字符范围。
def get_relative_citation_offsets(
    candidate: ContextCandidate,
) -> CitationWindowOffsets | None:
    context = candidate.context_chunk
    citation = candidate.citation_chunk

    if context.start_char is None or context.end_char is None:
        return None

    if citation.start_char is None or citation.end_char is None:
        return None

    if citation.start_char < context.start_char:
        return None

    if citation.end_char > context.end_char:
        return None

    relative_start = citation.start_char - context.start_char
    relative_end = citation.end_char - context.start_char

    if relative_start < 0 or relative_end < relative_start:
        return None

    if relative_end > len(context.content):
        return None

    return CitationWindowOffsets(
        start=relative_start,
        end=relative_end,
    )

# parent content:
#   A 段
#   B 段
#   C 段：真正命中的 child
#   D 段
# 拿到 B + C + D
def select_centered_context_window(
    context_text: str,
    offsets: CitationWindowOffsets,
    token_counter: TokenCounter,
    max_tokens: int,
) -> SelectedContextText:

    total_tokens = token_counter.count_text(context_text)

    if total_tokens <= max_tokens:
        selected_text = context_text.strip()
        return SelectedContextText(
            text=selected_text,
            truncated=False,
            token_count=token_counter.count_text(selected_text),
        )

    citation_center = (offsets.start + offsets.end) // 2

    estimated_chars = max_tokens * 4
    half_window = estimated_chars // 2

    window_start = max(0, citation_center - half_window)
    window_end = min(len(context_text), window_start + estimated_chars)

    if window_end - window_start < estimated_chars:
        window_start = max(0, window_end - estimated_chars)

    window_text = context_text[window_start:window_end].strip()

    if token_counter.count_text(window_text) > max_tokens:
        window_text = token_counter.truncate_text(
            window_text,
            max_tokens=max_tokens,
        )

    return SelectedContextText(
        text=window_text,
        truncated=True,
        token_count=token_counter.count_text(window_text),
    )


def select_context_text(
    candidate: ContextCandidate,
    token_counter: TokenCounter,
    max_chunk_tokens: int,
) -> SelectedContextText:

    content = candidate.context_chunk.content

    offsets = get_relative_citation_offsets(candidate)

    # 如果offsets不为空,走中心窗口
    if offsets is not None:
        return select_centered_context_window(
            context_text=content,
            offsets=offsets,
            token_counter=token_counter,
            max_tokens=max_chunk_tokens,
        )

    # 走普通token截断
    total_tokens = token_counter.count_text(content)

    if total_tokens <= max_chunk_tokens:
        selected_text = content.strip()
        return SelectedContextText(
            text=selected_text,
            truncated=False,
            token_count=token_counter.count_text(selected_text),
        )

    selected_text = token_counter.truncate_text(
        content.strip(),
        max_tokens=max_chunk_tokens,
    )

    return SelectedContextText(
        text=selected_text,
        truncated=True,
        token_count=token_counter.count_text(selected_text),
    )


# 1. sorted_candidates = sort_candidates(candidates)
# 2. 初始化 blocks / citations / used / dropped
# 3. total_tokens = 0
# 4. truncated = False
# 5. 遍历 sorted_candidates
# 6. citation_id = f"C{len(citations) + 1}"
# 7. selected = select_context_text(...)
# 8. block = format_context_block(citation_id, selected.text)
# 9. block_tokens = token_counter.count_text(block)
# 10. 如果 total_tokens + block_tokens > max_context_tokens:
#       dropped.append(candidate)
#       truncated = True
#       continue
# 11. preview = build_preview(candidate.citation_chunk.content, ...)
# 12. citation = build_citation(...)
# 13. append block / citation / used
# 14. total_tokens += block_tokens
# 15. truncated = truncated or selected.truncated
# 16. 返回 AssembledContext
def assemble_context(
    candidates: list[ContextCandidate],
    token_counter: TokenCounter,
    max_context_tokens: int,
    max_chunk_tokens: int,
    citation_preview_tokens: int = 80,
) -> AssembledContext:
    blocks: list[str] = []
    citations: list[AssembledCitation] = []
    used_candidates: list[ContextCandidate] = []
    dropped_candidates: list[ContextCandidate] = []

    total_tokens = 0
    truncated = False

    for candidate in sort_candidates(candidates):
        citation_id = f"C{len(citations) + 1}"

        selected_context = select_context_text(
            candidate=candidate,
            token_counter=token_counter,
            max_chunk_tokens=max_chunk_tokens,
        )

        if not selected_context.text:
            dropped_candidates.append(candidate)
            truncated = True
            continue

        block = format_context_block(
            citation_id=citation_id,
            content=selected_context.text,
        )
        block_tokens = token_counter.count_text(block)

        if total_tokens + block_tokens > max_context_tokens:
            dropped_candidates.append(candidate)
            truncated = True
            continue

        preview = build_preview(
            text=candidate.citation_chunk.content,
            token_counter=token_counter,
            max_preview_tokens=citation_preview_tokens,
        )

        citations.append(
            build_citation(
                citation_id=citation_id,
                candidate=candidate,
                preview=preview,
            )
        )
        blocks.append(block)
        used_candidates.append(candidate)
        total_tokens += block_tokens

        if selected_context.truncated:
            truncated = True

    return AssembledContext(
        context_text="\n\n".join(blocks),
        citations=citations,
        used_candidates=used_candidates,
        dropped_candidates=dropped_candidates,
        total_tokens=total_tokens,
        max_context_tokens=max_context_tokens,
        truncated=truncated,
    )