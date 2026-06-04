from uuid import uuid4

from app.models.document_chunk import DocumentChunk
from app.models.retrieval_types import ContextCandidate
from app.services.context_assembly_service import assemble_context_with_dynamic_budget
from app.rag.token_budget import (
    TokenBudgetRequest,
    build_dynamic_token_budget,
    build_token_budget_request_from_candidates,
)

class WhitespaceTokenCounter:
    def count_text(self, text: str) -> int:
        return len(text.split())

    def truncate_text(self, text: str, max_tokens: int) -> str:
        return " ".join(text.split()[:max_tokens])

def make_chunk(
        content: str,
        *,
        chunk_type: str,
        file_type: str = "txt",
        start_char: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        parent_id=None,
        chunk_type=chunk_type,
        chunk_index=0,
        content=content,
        content_hash="hash",
        token_count=len(content.split()),
        char_count=len(content),
        start_char=start_char,
        end_char=start_char + len(content),
        embedding_model=None,
        extra_metadata={"file_type": file_type},
    )

def test_assemble_context_with_dynamic_budget_uses_plan() -> None:
    parent_text = " ".join(f"token{i}" for i in range(200))
    child_text = " ".join(f"token{i}" for i in range(80, 100))

    parent = make_chunk(
        parent_text,
        chunk_type="parent",
        file_type="txt",
    )

    child_start = parent_text.index("token80")

    child = make_chunk(
        child_text,
        chunk_type="child",
        file_type="txt",
        start_char=child_start,
    )

    child.document_id = parent.document_id

    candidate = ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        retrieval_mode="parent_child",
        score=0.9,
    )

    assembled, plan = assemble_context_with_dynamic_budget(
        [candidate],
        token_counter=WhitespaceTokenCounter(),
        model_context_window=4096,
        task_type="qa",
    )

    assert plan.max_context_tokens > 0
    assert assembled.max_context_tokens == plan.max_context_tokens
    assert assembled.citations[0].citation_id == "C1"
    assert assembled.used_candidates == [candidate]

def test_dynamic_budget_parent_child_gets_larger_context_than_normal() -> None:
    normal_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            retrieval_mode="normal",
            candidate_count=5,
            document_types=("txt",),
        )
    )

    parent_child_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            retrieval_mode="parent_child",
            candidate_count=5,
            document_types=("txt",),
        )
    )

    assert parent_child_plan.max_context_tokens > normal_plan.max_context_tokens
    assert parent_child_plan.max_chunk_tokens >= 500

def test_dynamic_budget_code_documents_keep_wider_context_windows() -> None:
    text_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            retrieval_mode="parent_child",
            candidate_count=5,
            document_types=("txt",),
        )
    )

    code_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            retrieval_mode="parent_child",
            candidate_count=5,
            document_types=("md", "code"),
        )
    )

    assert code_plan.max_context_tokens > text_plan.max_context_tokens
    assert code_plan.max_chunk_tokens >= 700
    assert code_plan.citation_preview_tokens == 120

def test_dynamic_budget_reserves_history_and_answer_tokens() -> None:
    short_history_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            history_tokens=0,
        )
    )

    long_history_plan = build_dynamic_token_budget(
        TokenBudgetRequest(
            model_context_window=8192,
            history_tokens=3000,
        )
    )

    assert long_history_plan.available_prompt_tokens < short_history_plan.available_prompt_tokens
    assert long_history_plan.max_context_tokens < short_history_plan.max_context_tokens

def test_build_budget_request_infers_candidate_metadata() -> None:
    parent = make_chunk(
        "```python\ndef calculate():\n    return 1\n```",
        chunk_type="parent",
        file_type="md",
    )

    child = make_chunk(
        "def calculate():\n    return 1",
        chunk_type="child",
        file_type="md",
    )

    candidate = ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        retrieval_mode="parent_child",
    )

    request = build_token_budget_request_from_candidates([candidate])

    assert request.candidate_count == 1
    assert request.retrieval_mode == "parent_child"
    assert request.document_types == ("code", "md")