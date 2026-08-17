from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from core.models.base import Base

class TerritoryHistory(Base):
    __tablename__ = "territory_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    territory_id: Mapped[int] = mapped_column(Integer, nullable=False)
    modified_by: Mapped[str] = mapped_column(String(50), nullable=False)
    modified_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    field_changed: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)
    full_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))