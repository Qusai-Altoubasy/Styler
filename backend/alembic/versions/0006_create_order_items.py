"""create order_items table

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name_ar", sa.String(length=200), nullable=False),
        sa.Column("product_name_en", sa.String(length=200), nullable=False),
        sa.Column(
            "pricing_mode",
            sa.Enum(
                "fixed", "quote", name="pricing_mode", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("tier_note_ar", sa.String(length=200), nullable=True),
        sa.Column("tier_note_en", sa.String(length=200), nullable=True),
        sa.Column("color_name_ar", sa.String(length=50), nullable=True),
        sa.Column("color_name_en", sa.String(length=50), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=3), nullable=True),
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
        sa.CheckConstraint(
            "pricing_mode = 'quote' OR (quantity IS NOT NULL AND unit_price IS NOT NULL)",
            name=op.f("ck_order_items_fixed_item_is_priced"),
        ),
        sa.CheckConstraint("item_count >= 1", name=op.f("ck_order_items_item_count_positive")),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0", name=op.f("ck_order_items_quantity_positive")
        ),
        sa.CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0",
            name=op.f("ck_order_items_unit_price_not_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_items_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_order_items_product_id_products"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"])
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"])


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("order_items")
