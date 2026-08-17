from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.models.base import Base

if TYPE_CHECKING:
    from core.models.territory import Territory

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="jogador") # jogador, narrador, admin
    assigned_region: Mapped[str] = mapped_column(String(50), nullable=True) # Ex: Brasil, Espanha, Global
    clan: Mapped[str] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    territories: Mapped[List["Territory"]] = relationship(
        "Territory", 
        back_populates="owner",        # Nome da relação no modelo Territory
        cascade="all, delete-orphan"   # Se o usuário for deletado, apaga os territórios dele
    )

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_narrador(self) -> bool:
        return self.role in ["narrador", "admin"]

    def can_edit_region(self, region_name: str) -> bool:
        if self.is_narrador():
            return True
        return self.assigned_region == region_name or self.assigned_region == "Global"