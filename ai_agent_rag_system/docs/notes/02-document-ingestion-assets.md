# 学习笔记（二）：文档入库、解析与图片资产

记录日期：2026-05-11

第一份学习笔记已经完成 FastAPI 工程骨架和 `knowledge_bases` CRUD。本篇承接第一份：知识库只是容器，RAG 真正处理的是知识库下面的文档、文档解析结果、图片资产，以及后续要进入的 chunk。

本篇重点记录：

- `documents` 表设计。
- 文档登记接口。
- 本地资料入库脚本。
- txt / md 解析入口。
- Markdown 图片占位符解析。
- `document_assets` 表设计。
- 图片复制、URL 生成和资产入库。
- 解析脚本和文档状态推进。
- 本阶段遇到的典型错误。

## 1. 从知识库到文档

第一份笔记中的知识库 CRUD 解决的是：

```text
如何创建和管理知识库容器
```

但 RAG 不能直接检索知识库本身。真正被解析、切分、向量化和检索的是文档。

关系是：

```text
knowledge_bases
  -> documents
  -> document_assets
  -> document_chunks
```

一个知识库可以有多篇文档，一篇文档只属于一个知识库。

## 2. 为什么需要 documents 表

`documents` 表用于登记文件元数据，不保存完整原始文件内容。

它回答这些问题：

- 文件属于哪个知识库？
- 文件名是什么？
- 文件类型是什么？
- 文件保存在什么位置？
- 文件内容 hash 是什么？
- 当前处理到哪个阶段？
- 如果失败，失败原因是什么？

`documents` 表保存的是文件状态和索引信息，不是文件本体。

可以理解成：

```text
文件系统 / 对象存储：保存原始文件
documents 表：保存文件元数据和处理状态
document_chunks 表：保存可检索的文本片段
document_assets 表：保存图片等非文本资产
```

## 3. 为什么不把完整文件内容保存进 documents

文件内容通常是非结构化数据，例如 PDF、Word、Markdown、图片和长文本。直接放进关系数据库会带来问题：

- 数据库膨胀快，备份和迁移成本高。
- 查询文档列表时容易加载大字段。
- 文件预览、下载、解析更适合文件系统或对象存储。
- 后续从本地文件系统迁移到 MinIO、S3、CDN 时，只需要调整路径或 URL。

所以 `documents` 表只保存：

```text
文件是谁
文件在哪里
属于哪个知识库
当前处理状态
失败原因
追踪信息
```

## 4. Document 状态字段

文档入库不是一个瞬间完成的动作，而是一条流程：

```text
uploaded -> parsing -> parsed -> chunking -> indexed
```

失败时：

```text
failed
```

这些状态的含义：

- `uploaded`：文件已登记，还没有解析。
- `parsing`：正在解析。
- `parsed`：解析完成，文本和图片资产已处理。
- `chunking`：正在切分 chunk。
- `indexed`：chunk 和向量索引已完成，可以检索。
- `failed`：处理失败，需要查看 `error_message`。

没有 `status` 字段时，系统无法判断哪些文档该处理、哪些文档已完成、哪些文档需要重试。

## 5. Document 模型

模型文件：

```text
app/models/document.py
```

核心字段：

```text
id
knowledge_base_id
filename
file_type
file_path
file_hash
status
error_message
extra_metadata
created_at
updated_at
```

关键代码：

```python
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    knowledge_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="uploaded",
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
```

注意点：

- `knowledge_base_id` 是外键，指向 `knowledge_bases.id`。
- `file_hash` 要加索引，用于判断重复文件。
- `status` 要加索引，用于后台脚本筛选待处理文档。
- `metadata` 仍然使用 Python 属性 `extra_metadata` 映射，避免和 SQLAlchemy 内部属性冲突。

## 6. Document 迁移与 file_hash 索引

新增模型后要在：

```text
app/db/base.py
```

导入：

```python
from app.models.document import Document  # noqa: F401
```

否则 Alembic 可能看不到模型。

这次生成过两类迁移：

```text
32bfadf5771c_create_documents.py
42abb46cdedc_add_document_file_hash_index.py
```

原因是第一次创建 `documents` 表时，`file_hash` 没有加 `index=True`，后续补了一个索引迁移。

重要原则：

- 已经执行过的迁移不要随便改。
- 未执行的空迁移可以删除。
- 已执行后发现缺少字段或索引，应新增迁移补齐。

验证表结构：

```bash
docker exec postgres psql -U agent -d agent_workspace -c "\d documents"
```

应看到：

```text
ix_documents_file_hash
ix_documents_knowledge_base_id
ix_documents_status
documents_knowledge_base_id_fkey
```

## 7. Document Schema / Service / API

Schema 文件：

```text
app/schemas/document.py
```

核心结构：

```python
class DocumentCreate(BaseModel):
    knowledge_base_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    file_type: str = Field(min_length=1, max_length=50)
    file_path: str = Field(min_length=1)
    file_hash: str = Field(min_length=1, max_length=128)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    filename: str
    file_type: str
    file_path: str
    file_hash: str
    status: str
    error_message: str | None
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime
```

Service 文件：

```text
app/services/document_service.py
```

核心逻辑：

```python
def create_document(db: Session, data: DocumentCreate) -> Document:
    knowledge_base = db.get(KnowledgeBase, data.knowledge_base_id)

    if knowledge_base is None:
        raise ValueError("Knowledge base not found")

    document = Document(
        knowledge_base_id=data.knowledge_base_id,
        filename=data.filename,
        file_type=data.file_type,
        file_path=data.file_path,
        file_hash=data.file_hash,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document
```

列表查询支持按知识库过滤：

```python
def list_documents(
    db: Session,
    knowledge_base_id: UUID | None = None,
) -> list[Document]:
    statement = select(Document).order_by(Document.created_at.desc())

    if knowledge_base_id is not None:
        statement = statement.where(Document.knowledge_base_id == knowledge_base_id)

    result = db.execute(statement)
    return list(result.scalars().all())
```

API 文件：

```text
app/api/routes/documents.py
```

接口：

```text
POST /api/documents
GET  /api/documents
GET  /api/documents?knowledge_base_id=...
GET  /api/documents/{document_id}
```

知识点：

- `Query(default=None)` 表示查询参数。
- 创建文档前要检查知识库是否存在。
- service 可以抛 `ValueError` 表示业务错误，API 层转换成 HTTP 404。
- `DocumentRead` 的字段必须和 ORM 模型属性一致。

## 8. response_model 字段拼写问题

曾经把：

```python
extra_metadata
```

写成：

```python
extra_metadate
```

结果是：

```text
POST /api/documents 返回 Internal Server Error
GET /api/documents 却能查到数据
```

这说明：

```text
db.commit() 成功
db.refresh() 成功
return document
response_model 转换失败
FastAPI 返回 500
```

所以遇到 500 时，不只检查数据库写入，还要检查 `response_model` 和 ORM 字段是否对齐。

## 9. 本地资料入库脚本

脚本文件：

```text
scripts/register_local_documents.py
```

职责：

```text
扫描 data/ 目录
计算文件 hash
判断是否已登记
写入 documents 表
```

为什么放 `scripts/`：

- 它是本地批处理任务，不是对外 HTTP API。
- 不需要浏览器或前端调用。
- 适合数据初始化、维护、导入任务。

核心函数：

```python
def calculate_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
```

为什么用 hash：

- 同名文件内容可能不同。
- 不同文件名可能内容相同。
- hash 基于文件内容，比文件名更适合判断重复。

扫描文件：

```python
SUPPORTED_FILE_TYPES = {"txt", "md", "pdf", "docx"}


def iter_files(data_dir: Path) -> list[Path]:
    files: list[Path] = []

    for file_path in data_dir.rglob("*"):
        if not file_path.is_file():
            continue

        file_type = detect_file_type(file_path)

        if file_type not in SUPPORTED_FILE_TYPES:
            continue

        files.append(file_path)

    return sorted(files)
```

判断是否登记：

```python
def document_exists(db: Session, file_hash: str) -> bool:
    statement = select(Document.id).where(Document.file_hash == file_hash)
    result = db.execute(statement)
    return result.scalar_one_or_none() is not None
```

CLI 调用：

```bash
python scripts/register_local_documents.py \
  --knowledge-base-id c17c8b7d-0c5c-47bd-adfa-6f38dc1125f6 \
  --data-dir data
```

验证点：

- 第一次运行会登记新文档。
- 第二次运行应跳过已存在文件。
- 这叫幂等性。

## 10. 文档解析统一结构

解析模块：

```text
app/rag/loaders.py
```

统一返回结构：

```python
@dataclass
class ParsedAsset:
    source_path: str
    asset_type: str
    alt_text: str | None
    placeholder: str


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    assets: list[ParsedAsset] = field(default_factory=list)
```

为什么要统一结构：

- 不管来源是 txt、md、docx，后续 chunk splitter 都希望拿到同一种输入。
- `text` 用于切分 chunk。
- `metadata` 用于保留来源。
- `assets` 用于保存图片等非文本资源。

注意：

- Pydantic `BaseModel` 中用 `Field`。
- Python `dataclass` 中用 `field`。
- 这里要从 `dataclasses` 导入小写 `field`：

```python
from dataclasses import dataclass, field
```

不要误用：

```python
from pydantic import Field
```

## 11. txt 和 md loader

txt loader：

```python
def load_text_file(file_path: Path) -> ParsedDocument:
    text = file_path.read_text(encoding="utf-8")

    return ParsedDocument(
        text=text,
        metadata={
            "source": str(file_path),
            "file_type": file_path.suffix.lower().lstrip("."),
        },
        assets=[],
    )
```

Markdown 图片正则：

```python
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
```

Markdown loader：

```python
def load_markdown_file(file_path: Path) -> ParsedDocument:
    raw_text = file_path.read_text(encoding="utf-8")
    assets: list[ParsedAsset] = []

    def replace_image(match: re.Match[str]) -> str:
        alt_text = match.group(1) or None
        image_path = match.group(2)

        placeholder = f"[IMAGE:asset_{len(assets) + 1:03d}]"

        assets.append(
            ParsedAsset(
                source_path=image_path,
                asset_type="image",
                alt_text=alt_text,
                placeholder=placeholder,
            )
        )

        return placeholder

    text = MARKDOWN_IMAGE_PATTERN.sub(replace_image, raw_text)

    return ParsedDocument(
        text=text,
        metadata={
            "source": str(file_path),
            "file_type": "md",
        },
        assets=assets,
    )
```

`load_document()` 要按具体类型分发：

```python
def load_document(file_path: Path) -> ParsedDocument:
    file_type = file_path.suffix.lower().lstrip(".")

    if file_type in {"txt", "text"}:
        return load_text_file(file_path)

    if file_type == "md":
        return load_markdown_file(file_path)

    if file_type == "docx":
        raise NotImplementedError("docx will be implemented next")

    raise ValueError(f"Unsupported file type: {file_type}")
```

易错点：

- 不能先写 `if file_type in SUPPORTED_FILE_TYPES` 然后统一走 `load_text_file`。
- 否则 `md` 会被当成纯文本，图片不会被替换。

## 12. 为什么图片用 placeholder + assets

不要把图片二进制塞进 `ParsedDocument.text`。

原因：

- 文本切分器只适合处理文本。
- 图片二进制进入文本会破坏 chunk。
- 图片二进制进入 prompt 没有意义。
- chunk 存储会变得很大。
- 图片需要单独保存、预览、召回和展示。

正确结构：

```text
正文 text:
清理主刷如下图：

[IMAGE:asset_001]

请按图示拆卸主刷。
```

资产 assets：

```python
ParsedAsset(
    source_path="media/xxx.jpg",
    asset_type="image",
    alt_text=None,
    placeholder="[IMAGE:asset_001]",
)
```

后续：

- chunk 里保留 `[IMAGE:asset_001]`。
- `document_assets` 表保存图片 URL。
- 检索命中 chunk 时，根据 placeholder 找回图片。

## 13. Markdown 相对图片路径

Markdown 里可能写：

```md
![](media/17116181762913/17116187162894.jpg)
```

这个路径是相对于 md 文件所在目录的。

例如：

```text
data/md/数组.md
data/md/media/17116181762913/17116187162894.jpg
```

解析真实路径：

```python
source_document_path = Path(document.file_path)
source_path = Path(asset.source_path)

if not source_path.is_absolute():
    source_path = source_document_path.parent / source_path
```

## 14. document_assets 表

模型文件：

```text
app/models/document_asset.py
```

字段：

```text
id
document_id
asset_type
source_path
storage_path
url
alt_text
placeholder
extra_metadata
created_at
```

字段含义：

- `document_id`：属于哪个文档。
- `asset_type`：资产类型，第一版主要是 `image`。
- `source_path`：原始图片路径。
- `storage_path`：后端保存后的本地路径。
- `url`：前端可访问路径。
- `alt_text`：Markdown 图片 alt 文本，可以为空。
- `placeholder`：正文中的稳定占位符。
- `extra_metadata`：扩展信息。

为什么单独成表：

- 图片是独立资源，不只是文档 metadata。
- 后续要按 document 查询图片。
- 检索命中 chunk 后要根据 placeholder 找图片。
- 独立表更适合索引、关联、维护和迁移。

为什么同时有 `storage_path` 和 `url`：

```text
storage_path：后端保存和读取文件用
url：前端展示图片用
```

为什么不用 URL 直接写进正文：

- URL 可能随着存储迁移变化。
- placeholder 是稳定逻辑标识。
- chunk 里写 placeholder 比写长 URL 更干净。
- 前端展示时再把 placeholder 映射成真实 URL。

## 15. document_assets 迁移注意事项

迁移文件：

```text
migrations/versions/e349934e4513_create_document_assets.py
```

检查点：

- 是否创建 `document_assets` 表。
- `document_id` 是否有外键指向 `documents.id`。
- `document_id`、`asset_type`、`placeholder` 是否有索引。
- `metadata` 是否是 JSONB。
- `created_at` 是否是 `DateTime`。
- `alt_text` 是否允许为空。

这次遇到的问题：

```python
sa.Column("alt_text", sa.Text(), nullable=False)
```

但 Markdown 图片可以没有 alt：

```md
![](image.jpg)
```

所以应该是：

```python
sa.Column("alt_text", sa.Text(), nullable=True)
```

迁移执行后验证：

```bash
docker exec postgres psql -U agent -d agent_workspace -c "\d document_assets"
```

## 16. DocumentAsset Service

文件：

```text
app/services/document_asset_service.py
```

创建资产：

```python
def create_document_asset(
    db: Session,
    data: DocumentAssetCreate,
) -> DocumentAsset:
    document = db.get(Document, data.document_id)

    if document is None:
        raise ValueError("Document not found")

    asset = DocumentAsset(
        document_id=data.document_id,
        asset_type=data.asset_type,
        source_path=data.source_path,
        storage_path=data.storage_path,
        url=data.url,
        alt_text=data.alt_text,
        placeholder=data.placeholder,
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset
```

按文档列出资产：

```python
def list_document_assets(
    db: Session,
    document_id: UUID,
) -> list[DocumentAsset]:
    statement = (
        select(DocumentAsset)
        .where(DocumentAsset.document_id == document_id)
        .order_by(DocumentAsset.created_at.asc())
    )

    result = db.execute(statement)
    return list(result.scalars().all())
```

按 placeholder 查资产：

```python
def get_asset_by_placeholder(
    db: Session,
    document_id: UUID,
    placeholder: str,
) -> DocumentAsset | None:
    statement = select(DocumentAsset).where(
        DocumentAsset.document_id == document_id,
        DocumentAsset.placeholder == placeholder,
    )

    result = db.execute(statement)
    return result.scalar_one_or_none()
```

`get_asset_by_placeholder` 是后续图片召回的关键：chunk 命中 `[IMAGE:asset_001]` 后，可以用它找到对应图片 URL。

## 17. 保存解析出的图片资产

文件：

```text
app/services/document_parse_service.py
```

核心流程：

```text
load_document(document.file_path)
-> 遍历 parsed_document.assets
-> 解析图片真实路径
-> 复制图片到 app/static/assets/{document_id}/
-> 生成 /static/assets/{document_id}/xxx URL
-> 写入 document_assets
-> document.status = parsed
```

核心代码：

```python
def save_parsed_assets(db: Session, document: Document) -> None:
    parsed_document = load_document(Path(document.file_path))

    source_document_path = Path(document.file_path)
    asset_dir = Path(settings.static_dir) / "assets" / str(document.id)
    asset_dir.mkdir(parents=True, exist_ok=True)

    for asset in parsed_document.assets:
        existing_asset = get_asset_by_placeholder(
            db=db,
            document_id=document.id,
            placeholder=asset.placeholder,
        )

        if existing_asset is not None:
            print(f"SKIP existing asset: {asset.placeholder}")
            continue

        source_path = Path(asset.source_path)

        if not source_path.is_absolute():
            source_path = source_document_path.parent / source_path

        if not source_path.exists():
            document.status = "failed"
            document.error_message = f"Asset file not found: {source_path}"
            db.add(document)
            db.commit()
            raise FileNotFoundError(f"Asset file not found: {source_path}")

        suffix = source_path.suffix or ".bin"
        storage_filename = f"{asset.placeholder.strip('[]').replace(':', '_')}{suffix}"
        storage_path = asset_dir / storage_filename
        copy2(source_path, storage_path)

        url = f"/static/assets/{document.id}/{storage_filename}"

        create_document_asset(
            db=db,
            data=DocumentAssetCreate(
                document_id=document.id,
                asset_type=asset.asset_type,
                source_path=str(source_path),
                storage_path=str(storage_path),
                url=url,
                alt_text=asset.alt_text,
                placeholder=asset.placeholder,
            ),
        )

    document.status = "parsed"
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)
```

关键点：

- 先用 `get_asset_by_placeholder` 防止重复插入。
- 图片复制到 `app/static/assets/{document_id}/`。
- URL 使用 `/static/assets/{document_id}/...`，由 FastAPI 静态目录提供访问。
- 成功后状态改为 `parsed`。
- 图片缺失时状态改为 `failed`，并记录 `error_message`。

## 18. 解析脚本

脚本文件：

```text
scripts/parse_registered_documents.py
```

职责：

```text
读取 status = uploaded 的 documents
调用 save_parsed_assets()
成功 -> parsed
失败 -> failed
```

核心结构：

```python
from app.db import base  # noqa: F401
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.document_parse_service import save_parsed_assets
```

为什么要导入 `app.db.base`：

- 脚本直接操作 ORM。
- ORM 处理外键时需要相关模型都注册进同一个 metadata。
- `app.db.base` 会导入 `KnowledgeBase`、`Document`、`DocumentAsset` 等模型。
- 这个导入不是为了使用变量，而是为了触发模型注册。

查询待解析文档：

```python
statement = (
    select(Document)
    .where(
        Document.status == "uploaded",
        Document.file_type.in_(["txt", "text", "md"]),
    )
    .order_by(Document.created_at.asc())
)
```

注意：

- 当前已实现 txt 和 md。
- PDF 暂未实现 loader，不应该被标记为 failed。
- docx 图片抽取后续单独实现，因此第一版也可以先跳过。

运行：

```bash
python scripts/parse_registered_documents.py --limit 10
```

验证：

```bash
docker exec postgres psql -U agent -d agent_workspace -c "SELECT filename, file_type, status, error_message FROM documents ORDER BY created_at;"
```

## 19. 本阶段典型错误

### 19.1 dataclass 中误用 Pydantic Field

错误：

```python
from pydantic import Field

@dataclass
class ParsedDocument:
    assets: list[ParsedAsset] = Field(default_factory=list)
```

正确：

```python
from dataclasses import field

@dataclass
class ParsedDocument:
    assets: list[ParsedAsset] = field(default_factory=list)
```

结论：

- Pydantic `BaseModel` 用 `Field`。
- Python `dataclass` 用 `field`。

### 19.2 Markdown 没有走图片解析分支

错误写法：

```python
if file_type in SUPPORTED_FILE_TYPES:
    return load_text_file(file_path)

if file_type == "md":
    return load_markdown_file(file_path)
```

因为 `SUPPORTED_FILE_TYPES` 里包含 `md`，所以 md 会提前走 `load_text_file`，图片不会替换。

正确做法：

```python
if file_type in {"txt", "text"}:
    return load_text_file(file_path)

if file_type == "md":
    return load_markdown_file(file_path)
```

### 19.3 alt_text 不应该强制非空

Markdown 可以写：

```md
![](image.jpg)
```

这时 alt 文本为空，所以：

```python
alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### 19.4 直接运行脚本时模型没有全部注册

错误：

```text
NoReferencedTableError:
Foreign key associated with column 'documents.knowledge_base_id'
could not find table 'knowledge_bases'
```

原因：

- 当前 Python 进程只导入了 `Document`。
- 没有导入 `KnowledgeBase`。
- SQLAlchemy metadata 中缺少被外键引用的表。

解决：

```python
from app.db import base  # noqa: F401
```

### 19.5 脚本导入路径错误

错误：

```python
from models.document import Document
```

正确：

```python
from app.models.document import Document
```

项目内部导入应该使用完整包路径 `app...`。

### 19.6 PDF 暂未支持不等于解析失败

PDF loader 还没实现时，如果解析脚本直接处理 PDF，会得到：

```text
Unsupported file type: pdf
```

这不是文件坏了，而是功能暂未支持。

更合理的做法：

- 解析脚本先跳过 PDF。
- PDF 保持 `uploaded`。
- 等 PDF loader 实现后再处理。

## 20. 复习检查题

1. 第一份笔记中的 `knowledge_bases` 和本篇的 `documents` 是什么关系？
2. 为什么 `documents` 表不直接保存完整文件内容？
3. `file_path` 和 `file_hash` 分别解决什么问题？
4. 为什么文档处理需要 `status`？
5. 为什么本地资料入库脚本放在 `scripts/`，而不是 `app/api/routes/`？
6. 为什么 Markdown 图片不能直接塞进正文文本？
7. `ParsedDocument.text` 和 `ParsedDocument.assets` 分别保存什么？
8. Markdown 图片的相对路径应该如何解析成真实路径？
9. 为什么 `document_assets` 要单独成表？
10. `storage_path` 和 `url` 有什么区别？
11. 为什么 chunk 文本里保存 placeholder，而不是保存图片 URL？
12. 为什么 `alt_text` 应该允许为空？
13. 重复执行 `save_parsed_assets` 时，如何避免重复插入图片资产？
14. 为什么脚本里要导入 `from app.db import base`？
15. 为什么 PDF 暂未支持时不应该直接标记为 failed？
