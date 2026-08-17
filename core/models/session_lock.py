from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from core.models.base import Base

class SessionLock(Base):
    __tablename__ = "session_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    territory_id: Mapped[int] = mapped_column(Integer, nullable=False)
    locked_by: Mapped[str] = mapped_column(String(50), nullable=False)
    locked_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1)