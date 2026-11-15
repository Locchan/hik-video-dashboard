from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint, false
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConfigEntry(Base):
    __tablename__ = "config"
    __table_args__ = (
        UniqueConstraint("name", "group_read", name="uq_config_name_group_read"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    group_read: Mapped[int] = mapped_column(ForeignKey("api_group.id"), nullable=False)
    group_write: Mapped[int] = mapped_column(ForeignKey("api_group.id"), nullable=False)
    protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
