from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_asset import DocumentAssets
from app.schemas.document_asset import DocumentAssetCreate

def create_document_asset(db:Session,data:DocumentAssetCreate)->DocumentAssets:

    document = db.get(Document,data.document_id)
    if document is None:
        raise ValueError("Document not found")

    asset = DocumentAssets(
        document_id = data.document_id,
        asset_type = data.asset_type,
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

def list_document_assets(db:Session,document_id:UUID) -> list[DocumentAssets]:
    statement = (select(DocumentAssets).where(DocumentAssets.document_id==document_id)
                 .order_by(DocumentAssets.created_at.asc()))

    result = db.execute(statement)
    return list(result.scalars().all())

def get_asset_by_placeholder(db:Session,document_id:UUID,placeholder:str) -> DocumentAssets | None:
    '''
    通过placeholder找图片
    :param db:
    :param document_id:
    :param placeholder:
    :return:
    '''
    statement = (select(DocumentAssets)
                 .where(DocumentAssets.document_id==document_id,DocumentAssets.placeholder==placeholder))
    result = db.execute(statement)
    return result.scalar_one_or_none()