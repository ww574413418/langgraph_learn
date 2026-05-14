from dataclasses import dataclass,field
from langchain_text_splitters import RecursiveCharacterTextSplitter,MarkdownTextSplitter
import re

# 定义md标题提取正则
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class SplitChunk:
    '''
    保存文本块信息
    '''
    content:str
    chunk_index:int
    start_char:int | None = None
    end_char:int | None = None
    metadata:dict = field(default_factory=dict)

@dataclass
class ParentChildSplit:
    parent:SplitChunk
    children:list[SplitChunk]


def build_text_splitter(file_type:str,
                        chunk_size:int,
                        chunk_overlap:int) :

    if file_type == "md":
        return MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True
        )


    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            ".",
            " ",
            "",
        ],
        keep_separator=True,
        add_start_index=True,
    )


def split_normal_chunks(text:str,file_type:str,
                        chunk_size:int=1000,
                        chunk_overlap:int=120,
                        min_chunk_size:int=120) -> list[SplitChunk]:

    splitter = build_text_splitter(file_type, chunk_size, chunk_overlap)

    headings = extract_markdown_headings(text) if file_type == "md" else []


    docs = splitter.create_documents(
        [text],
        metadatas=[{"file_type":file_type,"chunk_strategy":"normal"}]
    )

    chunks:list[SplitChunk] = []

    for index, doc in enumerate(docs):
        metadata = dict(doc.metadata)
        start_char = metadata.pop("start_index", None)
        end_char = (
            start_char + len(doc.page_content)
            if start_char is not None
            else None
        )

        heading_metadata = find_heading_metadata(
            headings=headings,
            start_char=start_char,
            end_char=end_char,
        )

        metadata = {
            **heading_metadata,
            **metadata,
        }

        chunks.append(
            SplitChunk(
                content=doc.page_content,
                chunk_index=index,
                start_char=start_char,
                end_char=(
                    start_char + len(doc.page_content)
                    if start_char is not None
                    else None
                ),
                metadata=metadata,
            )
        )

    return merge_small_chunks(chunks, min_chunk_size=min_chunk_size)



def extract_markdown_headings(text: str) -> list[str]:
    '''
    提取md文件中的标题
    '''
    headings:list[dict] = []

    current_path:dict[int,str] = {}

    for match in HEADING_PATTERN.finditer(text):
        level = len(match.group(1))
        title = match.group(2).strip()
        position = match.start()

        current_path[level] = title

        for old_level in list(current_path.keys()):
            if old_level > level:
                del current_path[old_level]

        metadata = {
            f"heading_{heading_level}":current_path[heading_level] for heading_level in sorted(current_path)
        }

        headings.append({
            "position": position,
            "level": level,
            "title": title,
            "metadata": metadata,
        })

    return headings

def find_heading_metadata(
    headings: list[dict],
    start_char: int | None,
    end_char: int | None = None,
) -> dict:
    if start_char is None:
        return {}

    matched: dict = {}

    for heading in headings:
        position = heading["position"]

        if position <= start_char:
            matched = heading["metadata"]
            continue

        if end_char is not None and start_char < position < end_char:
            matched = heading["metadata"]
            continue

        if end_char is not None and position >= end_char:
            break

    return dict(matched)



# 处理小chunk 太小的chunk进行合并
def merge_metadata(left:dict,right:dict) -> dict:
    return {
        **left,
        **right,
    }

def merge_small_chunks(chunks:list[SplitChunk],min_chunk_size:int=120)->list[SplitChunk]:
    if not chunks:
        return []

    merged:list[SplitChunk] = []

    for chunk in chunks:
        if len(chunk.content.strip()) >= min_chunk_size:
            merged.append(chunk)
            continue

        if not merged:
            merged.append(chunk)
            continue

        previous = merged[-1]

        merged_content = previous.content.lstrip() + "\n\n" + chunk.content.lstrip()

        merged[-1] = SplitChunk(
            content=merged_content,
            chunk_index=previous.chunk_index,
            start_char=previous.start_char,
            end_char=chunk.end_char or previous.end_char,
            metadata=merge_metadata(previous.metadata, chunk.metadata),
        )

    reindexed:list[SplitChunk] = []

    for index, chunk in enumerate(merged):
        reindexed.append(
            SplitChunk(
                content=chunk.content,
                chunk_index=index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                metadata=chunk.metadata,
            )
        )

    return reindexed