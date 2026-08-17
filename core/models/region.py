from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.models.base import Base

if TYPE_CHECKING:
    from core.models.territory import Territory

class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_type: Mapped[str] = mapped_column(String(20), default="pais")
    center_lat: Mapped[float] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float] = mapped_column(Float, nullable=True)
    zoom_level: Mapped[int] = mapped_column(Integer, default=6)

    territories: Mapped[List["Territory"]] = relationship("Territory", back_populates="region")