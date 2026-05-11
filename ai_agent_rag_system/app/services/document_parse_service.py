from pathlib import Path
from shutil import copy2
from uuid import UUID
# 而是为了触发模型导入注册。
from app.db import base  # noqa: F401
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document
from app.rag.loaders import load_document
from app.schemas.document_asset import DocumentAssetCreate
from app.services.document_asset_service import create_document_asset
from app.services.document_asset_service import create_document_asset,get_asset_by_placeholder

def save_parsed_assets(db:Session,document:Document)->None:
    parsed_document = load_document(Path(document.file_path))

    source_document_path = Path(document.file_path)
    asset_dir = Path(settings.static_dir)/"assets"/str(document.id)
    asset_dir.mkdir(parents=True,exist_ok=True)

    for asset in parsed_document.assets:
        # 判断图片是否被处理过
        existing_asset = get_asset_by_placeholder(db,document.id,asset.placeholder)

        if existing_asset is not None:
            print(f"SKIP existing asset:{asset.placeholder}")
            continue

        source_path = Path(asset.source_path)

        if not source_path.is_absolute():
            source_path = source_document_path.parent/source_path

        if not source_path.exists():
            document.status = "failed"
            document.error_message = f"Asset file not found:{source_path}"
            db.add(document)
            db.commit()
            raise FileNotFoundError(f"Asset file not found:{source_path}")

        suffix = source_path.suffix or ".bin"
        storage_filename = f"{asset.placeholder.strip('[]').replace(':','_')}{suffix}"
        storage_path = asset_dir/storage_filename
        copy2(source_path,storage_path)

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
                placeholder=asset.placeholder
            )
        )

    document.status = "parsed"
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)
