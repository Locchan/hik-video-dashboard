"""Filesystem scan for Hik alert clips and snaps."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select

from hvd.models import Alert

# Filename wall-clock times are GMT+3 (not DST-aware).
_FILENAME_TZ = timezone(timedelta(hours=3))
_TS_RE = re.compile(r"^(\d{8})_(\d{6})")
_CLIP_EXTS = {".mp4", ".MP4"}
_SNAP_EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


@dataclass(frozen=True)
class ClipInfo:
    timestamp: datetime
    camera: str
    path: str


def alerts_dir() -> Path:
    return Path(os.environ.get("ALERTS_DIR", "/alerts"))


def parse_alert_timestamp(name: str) -> datetime | None:
    """Parse leading YYYYMMDD_HHMMSS as GMT+3 and return UTC."""
    base = Path(name).name
    m = _TS_RE.match(base)
    if not m:
        return None
    try:
        local = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(
            tzinfo=_FILENAME_TZ
        )
        return local.astimezone(timezone.utc)
    except ValueError:
        return None


def list_clip_files(root: Path | None = None) -> list[ClipInfo]:
    base = root if root is not None else alerts_dir()
    clip_root = base / "J_HikAlertClip"
    out: list[ClipInfo] = []
    if not clip_root.is_dir():
        return out
    for camera_dir in sorted(p for p in clip_root.iterdir() if p.is_dir()):
        camera = camera_dir.name
        for path in camera_dir.rglob("*"):
            if not path.is_file() or path.suffix not in _CLIP_EXTS:
                continue
            ts = parse_alert_timestamp(path.name)
            if ts is None:
                continue
            out.append(ClipInfo(timestamp=ts, camera=camera, path=str(path.resolve())))
    out.sort(key=lambda c: c.timestamp, reverse=True)
    return out


def find_nearest_snap(camera: str, timestamp: datetime, root: Path | None = None) -> Path | None:
    base = root if root is not None else alerts_dir()
    snap_dir = base / "J_HikAlertSnap" / camera
    if not snap_dir.is_dir():
        return None
    best: Path | None = None
    best_delta: float | None = None
    for path in snap_dir.iterdir():
        if not path.is_file() or path.suffix not in _SNAP_EXTS:
            continue
        ts = parse_alert_timestamp(path.name)
        if ts is None:
            continue
        delta = abs((ts - timestamp).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = path
    return best


def sync_alerts_to_db(session_factory: Callable, root: Path | None = None) -> list[dict]:
    """Upsert discovered clips; return alert dicts newer→older."""
    clips = list_clip_files(root)
    with session_factory() as session:
        for clip in clips:
            existing = session.scalar(
                select(Alert).where(
                    Alert.camera == clip.camera,
                    Alert.timestamp == clip.timestamp,
                )
            )
            if existing is None:
                by_path = session.scalar(select(Alert).where(Alert.path == clip.path))
                if by_path is not None:
                    by_path.timestamp = clip.timestamp
                    by_path.camera = clip.camera
                else:
                    session.add(
                        Alert(
                            timestamp=clip.timestamp,
                            camera=clip.camera,
                            path=clip.path,
                        )
                    )
            elif existing.path != clip.path:
                existing.path = clip.path
        session.commit()
        rows = session.scalars(
            select(Alert).order_by(Alert.timestamp.desc(), Alert.id.desc())
        ).all()
        return [
            {
                "video_id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "camera": r.camera,
                "path": r.path,
            }
            for r in rows
        ]
