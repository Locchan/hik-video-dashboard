from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    LargeBinary,
    Text,
    UniqueConstraint,
    false,
)
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
    protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class FeatureFlag(Base):
    """Feature on/off state. Descriptions live in ``hvd.features.FEATURES``."""

    __tablename__ = "features"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        UniqueConstraint("camera", "timestamp", name="uq_alert_camera_timestamp"),
        UniqueConstraint("path", name="uq_alert_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    camera: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)


class AlertThumbnail(Base):
    __tablename__ = "alert_thumbnail"
    __table_args__ = (
        UniqueConstraint("camera", "timestamp", name="uq_alert_thumbnail_camera_timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    camera: Mapped[str] = mapped_column(Text, nullable=False)
    png: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
