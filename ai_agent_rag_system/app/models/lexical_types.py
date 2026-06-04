from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LexicalChunkDocument:
    chunk_id: UUID
    document_id: UUID
    parent_id: UUID | None
    chunk_type: str
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    char_count: int
    start_char: int
    end_char: int
    filename: str | None = None
    section_title: str | None = None
    extra_metadata: dict | None = None