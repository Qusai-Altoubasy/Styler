"""create products table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name_ar", sa.String(length=200), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("description_ar", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("description_en", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("image_key", sa.String(length=255), nullable=True),
        sa.Column(
            "pricing_mode",
            sa.Enum(
                "fixed", "quote", name="pricing_mode", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("free_delivery", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_products_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"])


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("products")
