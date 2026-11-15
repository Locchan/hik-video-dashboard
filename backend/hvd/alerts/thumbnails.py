"""Build and cache alert thumbnails as PNG bytes."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image
from sqlalchemy import select

from hvd.alerts.scanner import alerts_dir, find_nearest_snap
from hvd.models import Alert, AlertThumbnail


class ThumbnailError(Exception):
    """Could not produce a thumbnail for an alert."""


def _resize_to_quarter_png(image_path: Path) -> bytes:
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        # 4x smaller → quarter width and height
        size = (max(1, w // 4), max(1, h // 4))
        img = img.resize(size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def get_or_create_thumbnail_png(
    session_factory: Callable,
    *,
    video_id: int,
    root: Path | None = None,
) -> tuple[bytes, datetime, str]:
    """Return (png_bytes, timestamp, camera) for alert id; raise ThumbnailError."""
    with session_factory() as session:
        alert = session.get(Alert, video_id)
        if alert is None:
            raise ThumbnailError(f"alert {video_id} not found")
        camera = alert.camera
        timestamp = alert.timestamp

        cached = session.scalar(
            select(AlertThumbnail).where(
                AlertThumbnail.camera == camera,
                AlertThumbnail.timestamp == timestamp,
            )
        )
        if cached is not None and cached.png:
            return bytes(cached.png), timestamp, camera

        snap = find_nearest_snap(camera, timestamp, root=root if root is not None else alerts_dir())
        if snap is None:
            raise ThumbnailError(f"no snap found for camera {camera}")
        try:
            png = _resize_to_quarter_png(snap)
        except Exception as e:
            raise ThumbnailError(f"failed to resize snap: {e}") from e

        row = AlertThumbnail(timestamp=timestamp, camera=camera, png=png)
        session.add(row)
        session.commit()
        return png, timestamp, camera
