"""create product_colors table

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_colors",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name_ar", sa.String(length=50), nullable=False),
        sa.Column("name_en", sa.String(length=50), nullable=False),
        sa.Column("hex", sa.String(length=7), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("hex ~ '^#[0-9a-f]{6}$'", name=op.f("ck_product_colors_hex_format")),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_colors_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_colors")),
    )
    op.create_index(op.f("ix_product_colors_product_id"), "product_colors", ["product_id"])


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("product_colors")
