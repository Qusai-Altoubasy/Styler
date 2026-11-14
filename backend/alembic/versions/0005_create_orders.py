"""create orders table

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1001), nullable=False),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=False),
        sa.Column(
            "governorate",
            sa.Enum(
                "amman",
                "zarqa",
                "irbid",
                "balqa",
                "madaba",
                "mafraq",
                "jerash",
                "ajloun",
                "karak",
                "tafilah",
                "maan",
                "aqaba",
                name="governorate",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "done", "cancelled", name="order_status", native_enum=False, create_constraint=True
            ),
            nullable=True,
        ),
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
        sa.CheckConstraint("phone ~ '^07[789][0-9]{7}$'", name=op.f("ck_orders_phone_format")),
        sa.CheckConstraint("delivery_fee >= 0", name=op.f("ck_orders_delivery_fee_not_negative")),
        sa.CheckConstraint("subtotal >= 0", name=op.f("ck_orders_subtotal_not_negative")),
        sa.CheckConstraint("total >= 0", name=op.f("ck_orders_total_not_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index(op.f("ix_orders_phone"), "orders", ["phone"])


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("orders")
