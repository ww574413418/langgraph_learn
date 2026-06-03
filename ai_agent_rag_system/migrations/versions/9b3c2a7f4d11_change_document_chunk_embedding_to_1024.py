"""change document chunk embedding to 1024 dimensions

Revision ID: 9b3c2a7f4d11
Revises: 1ed2530eec8c
Create Date: 2026-06-03 16:20:00.000000

"""

from typing import Sequence, Union

import pgvector.sqlalchemy
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b3c2a7f4d11"
down_revision: Union[str, Sequence[str], None] = "1ed2530eec8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade embedding storage from vector(8) to vector(1024)."""
    # 8 维 embedding 只是前期测试用的占位向量。
    # 切到 1024 维后，旧向量不能继续使用：
    # - 数学维度不匹配，pgvector 不能把 vector(8) 当 vector(1024) 检索。
    # - 即使用补零方式凑够维度，语义空间也不是同一个模型生成的，检索结果不可信。
    #
    # 因此生产迁移策略是：
    # 1. 清空旧 embedding。
    # 2. 修改列类型为 vector(1024)。
    # 3. 迁移完成后重新跑索引任务，用真实 1024 维模型重新生成 embedding。
    op.execute(
        """
        UPDATE document_chunks
        SET
            embedding = NULL,
            embedding_model = NULL,
            embedding_dimensions = NULL
        WHERE embedding IS NOT NULL
           OR embedding_model IS NOT NULL
           OR embedding_dimensions IS NOT NULL
        """
    )

    op.alter_column(
        "document_chunks",
        "embedding",
        type_=pgvector.sqlalchemy.Vector(dim=1024),
        existing_type=pgvector.sqlalchemy.Vector(dim=8),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade embedding storage from vector(1024) back to vector(8)."""
    # 降级同样不能复用 1024 维向量，所以先清空再改列类型。
    op.execute(
        """
        UPDATE document_chunks
        SET
            embedding = NULL,
            embedding_model = NULL,
            embedding_dimensions = NULL
        WHERE embedding IS NOT NULL
           OR embedding_model IS NOT NULL
           OR embedding_dimensions IS NOT NULL
        """
    )

    op.alter_column(
        "document_chunks",
        "embedding",
        type_=pgvector.sqlalchemy.Vector(dim=8),
        existing_type=pgvector.sqlalchemy.Vector(dim=1024),
        nullable=True,
    )
