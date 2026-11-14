"""create product_price_tiers table

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_price_tiers",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("note_ar", sa.String(length=200), nullable=True),
        sa.Column("note_en", sa.String(length=200), nullable=True),
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
        sa.CheckConstraint("price >= 0", name=op.f("ck_product_price_tiers_price_not_negative")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_product_price_tiers_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_price_tiers_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_price_tiers")),
    )
    op.create_index(
        op.f("ix_product_price_tiers_product_id"), "product_price_tiers", ["product_id"]
    )
    # Same quantity allowed with a different note; exact duplicates refused.
    op.create_index(
        "uq_product_price_tiers_tier",
        "product_price_tiers",
        ["product_id", "quantity", "note_ar", "note_en"],
        unique=True,
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("product_price_tiers")
