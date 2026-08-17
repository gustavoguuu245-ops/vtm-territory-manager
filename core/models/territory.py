from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.models.base import Base

if TYPE_CHECKING:
    from core.models.region import Region
    from core.models.user import User
    
class Territory(Base):
    __tablename__ = "territories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geojson_polygon: Mapped[str] = mapped_column(Text, nullable=True)
    
    controlling_clan: Mapped[str] = mapped_column(String(30), default="Neutro")
    influence_level: Mapped[int] = mapped_column(Integer, default=1)
    danger_level: Mapped[int] = mapped_column(Integer, default=1)
    map_color: Mapped[str] = mapped_column(String(10), default="#808080")
    
    version: Mapped[int] = mapped_column(Integer, default=1) # Optimistic Locking
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    
    created_by: Mapped[str] = mapped_column(String(50), nullable=True)
    modified_by: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    #id usarios 
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    owner: Mapped["User"] = relationship("User", back_populates="territories")
    region: Mapped["Region"] = relationship("Region", back_populates="territories")