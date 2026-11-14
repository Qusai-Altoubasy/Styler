"""create settings table

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column(
            "id", sa.Integer(), server_default=sa.text("1"), autoincrement=False, nullable=False
        ),
        sa.Column("zone_a_delivery_fee", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("zone_b_delivery_fee", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("whatsapp_number", sa.String(length=10), nullable=False),
        sa.Column("instagram_url", sa.String(length=500), nullable=True),
        sa.Column("facebook_url", sa.String(length=500), nullable=True),
        sa.Column("admin_password_hash", sa.String(length=255), nullable=True),
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
        sa.CheckConstraint("id = 1", name=op.f("ck_settings_single_row")),
        sa.CheckConstraint(
            "zone_a_delivery_fee >= 0", name=op.f("ck_settings_zone_a_delivery_fee_not_negative")
        ),
        sa.CheckConstraint(
            "zone_b_delivery_fee >= 0", name=op.f("ck_settings_zone_b_delivery_fee_not_negative")
        ),
        sa.CheckConstraint(
            "whatsapp_number ~ '^07[789][0-9]{7}$'", name=op.f("ck_settings_whatsapp_format")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings")),
    )


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("settings")
