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



def extract_markdown_headings(text: str) -> list[dict]:
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

# 父子切片
def split_parent_child_chunks(
        text:str,
        file_type:str,
        parent_chunk_size:int=1800,
        parent_chunk_overlap:int=120,
        child_chunk_size:int=400,
        child_chunk_overlap:int=80
)->list[ParentChildSplit]:
    '''
    1. 先用 parent splitter 把全文切成 parent chunks
    2. 遍历每个 parent
    3. 对 parent.content 再用 child splitter 切成 children
    4. 每个 child 的 start_char / end_char 要换算回全文坐标
    5. 返回 ParentChildSplit(parent=parent, children=children)
    '''
    headings = extract_markdown_headings(text) if file_type == "md" else []

    # 对父块进行切块
    parent_chunks:list[SplitChunk] = split_normal_chunks(
        text=text,
        file_type=file_type,
        chunk_size=parent_chunk_size,
        chunk_overlap=parent_chunk_overlap,
    )

    results:list[ParentChildSplit] = []

    # 遍历每个父块,然后将每个父块切分成若干子块
    for parent_index,parent in enumerate(parent_chunks):
        # 获取切分器
        child_splitter = build_text_splitter(file_type, child_chunk_size, child_chunk_overlap)

        child_docs= child_splitter.create_documents(
            texts=[parent.content],
            metadatas=[{"file_type":file_type,"chunk_strategy":"parent_child"}]
        )

        children:list[SplitChunk] = []

        # 将子块转为 SplitChunk
        for child_index,child_doc in enumerate(child_docs):
            metadata = dict(child_doc.metadata)
            child_start_in_parent = metadata.pop("start_index",None)

            if parent.start_char is not None and child_start_in_parent is not None:
                start_char = parent.start_char + child_start_in_parent
                end_char = start_char + len(child_doc.page_content)
            else:
                start_char = None
                end_char = None

            # 获取子块标题
            heading_metadata = find_heading_metadata(
                headings=headings,
                start_char=start_char,
                end_char=end_char,
            )
            
            metadata = {
                **remove_heading_metadata(parent.metadata),
                **heading_metadata,
                **metadata,
            }

            children.append(
                SplitChunk(
                    content=child_doc.page_content,
                    chunk_index=child_index,
                    start_char=start_char,
                    end_char=end_char,
                    metadata=metadata,
                )
            )

        # 合并太小的chunk
        children =  merge_small_chunks( children, min_chunk_size=80)

        parent_heading_metadata = find_heading_at_position(
            headings=headings,
            position=parent.start_char,
        )

        results.append(
            ParentChildSplit(
                parent=SplitChunk(
                    content=parent.content,
                    chunk_index=parent_index,
                    start_char=parent.start_char,
                    end_char=parent.end_char,
                    metadata={
                        **remove_heading_metadata(parent.metadata),
                        **parent_heading_metadata,
                        "chunk_strategy": "parent_child",
                        "chunk_role": "parent",
                        "parent_chunk_size": parent_chunk_size,
                        "parent_chunk_overlap": parent_chunk_overlap,
                    },
                ),
                children=[
                    SplitChunk(
                        content=child.content,
                        chunk_index=child.chunk_index,
                        start_char=child.start_char,
                        end_char=child.end_char,
                        metadata={
                            **child.metadata,
                            "chunk_role": "child",
                            "child_chunk_size": child_chunk_size,
                            "child_chunk_overlap": child_chunk_overlap,
                        },

                    )
                    for child in children
                ]
            )
        )

    return results


# 再根据 parent.start_char 重新找标题：
def find_heading_at_position(
    headings: list[dict],
    position: int | None,
) -> dict:
    if position is None:
        return {}

    matched: dict = {}

    for heading in headings:
        if heading["position"] <= position:
            matched = heading["metadata"]
            continue

        break

    return dict(matched)

# 先删掉 parent.metadata 里旧的 heading 字段：
def remove_heading_metadata(metadata: dict) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if not key.startswith("heading_")
    }
