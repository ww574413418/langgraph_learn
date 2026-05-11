from dataclasses import dataclass,field
from pathlib import Path
import re

@dataclass
class ParsedAsset:
    '''
    保存markdown中的图片信息
    '''
    source_path:str
    asset_type:str
    alt_text:str | None
    placeholder:str

@dataclass
class ParsedDocument:
    '''
    统一数据结构
    '''
    text:str
    metadata:dict
    assets:list[ParsedAsset] = field(default_factory=list)



def load_text_file(file_path:Path)->ParsedDocument:
    text = file_path.read_text(encoding="utf-8")

    return ParsedDocument(
        text=text,
        metadata={
            "source":str(file_path),
            "file_type":file_path.suffix.lower().lstrip(".")
        },
        assets=[],
    )

MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

def load_markdown_file(file_path:Path) -> ParsedDocument:
    raw_text = file_path.read_text(encoding="utf-8")

    assets:list[ParsedAsset] = []

    def replace_image(match:re.Match[str]) -> str:
        alt_text = match.group(1) or None
        image_path = match.group(2)

        placeholder = f"[IMAGE:asset_{len(assets) + 1:03d}]"

        assets.append(
            ParsedAsset(
                source_path=image_path,
                asset_type="image",
                alt_text=alt_text,
                placeholder=placeholder
            )
        )

        return placeholder

    text = MARKDOWN_IMAGE_PATTERN.sub(replace_image,raw_text)

    return ParsedDocument(
        text=text,
        metadata={
            "source":str(file_path),
            "file_type":"md"
        },
        assets=assets
    )

def load_document(file_path:Path)->ParsedDocument:
    file_type = file_path.suffix.lower().lstrip(".")

    if file_type in {"txt","text"}:
        return load_text_file(file_path)

    if file_type == "md":
        return load_markdown_file(file_path)

    if file_type == "docx":
        raise NotImplementedError("docx will be implemented next")

    raise ValueError(f"Unsupported file type: {file_type}")