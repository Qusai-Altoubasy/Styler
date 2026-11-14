"""create categories table

Revision ID: 0001
Revises:
Create Date: 2026-11-14 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name_ar", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column(
            "color",
            sa.Enum(
                "cyan",
                "magenta",
                "yellow",
                "black",
                name="brand_color",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("image_key", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    # Unique ignoring case and surrounding spaces, among live rows.
    op.create_index(
        "uq_categories_name_ar",
        "categories",
        [sa.text("lower(btrim(name_ar))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_categories_name_en",
        "categories",
        [sa.text("lower(btrim(name_en))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.drop_table("categories")
