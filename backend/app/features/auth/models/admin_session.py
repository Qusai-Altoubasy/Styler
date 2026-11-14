from datetime import datetime

from sqlalchemy import DateTime, Identity, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SOFT_DELETE_FILTER, Base, SoftDeleteMixin, TimestampMixin


class AdminSession(TimestampMixin, SoftDeleteMixin, Base):
    """An open manager session (one per device).

    The cookie holds a random token; only its SHA-256 hash is stored. Logging out,
    changing the password or "log out of all devices" soft-deletes the rows.
    """

    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "uq_admin_sessions_token_hash",
            "token_hash",
            unique=True,
            postgresql_where=text(SOFT_DELETE_FILTER),
        ),
    )
