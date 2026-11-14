"""seed settings

The single settings row with the store's starting values, so the store can take
orders (delivery fees, WhatsApp number) before the manager opens the settings tab.
The manager changes all of it from the dashboard afterwards.

A plain table definition instead of the app model: a migration must keep working
even after the model changes.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14 19:00:00
"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

settings = sa.table(
    "settings",
    sa.column("id", sa.Integer),
    sa.column("zone_a_delivery_fee", sa.Numeric),
    sa.column("zone_b_delivery_fee", sa.Numeric),
    sa.column("whatsapp_number", sa.String),
    sa.column("instagram_url", sa.String),
    sa.column("facebook_url", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        settings,
        [
            {
                "id": 1,
                "zone_a_delivery_fee": Decimal("2.000"),  # Amman and Zarqa
                "zone_b_delivery_fee": Decimal("3.000"),  # every other governorate
                "whatsapp_number": "0790087017",
                "instagram_url": "https://www.instagram.com/styler_printing.press",
                "facebook_url": "https://www.facebook.com/profile.php?id=61594519182687",
            }
        ],
    )


def downgrade() -> None:
    """Local development only. On the server, roll back from the pg_dump."""
    op.execute(sa.delete(settings).where(settings.c.id == 1))
