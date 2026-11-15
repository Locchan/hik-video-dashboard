from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hvd.alerts.scanner import find_nearest_snap, list_clip_files, parse_alert_timestamp


def test_parse_alert_timestamp():
    # Filename wall time is GMT+3 → store UTC (11:56:10 +03 → 08:56:10Z).
    ts = parse_alert_timestamp("20261114_115610_reg_dacha.mp4")
    assert ts == datetime(2026, 11, 14, 8, 56, 10, tzinfo=timezone.utc)
    assert parse_alert_timestamp("nope.mp4") is None


def test_list_clips_and_nearest_snap(tmp_path: Path):
    clip = tmp_path / "J_HikAlertClip" / "cam4_dacha"
    snap = tmp_path / "J_HikAlertSnap" / "cam4_dacha"
    clip.mkdir(parents=True)
    snap.mkdir(parents=True)
    (clip / "20261114_115610_reg_dacha.mp4").write_bytes(b"x")
    (snap / "20261114_115615_cam4_dacha.jpg").write_bytes(b"y")
    (snap / "20261114_100000_cam4_dacha.jpg").write_bytes(b"z")

    clips = list_clip_files(tmp_path)
    assert len(clips) == 1
    assert clips[0].camera == "cam4_dacha"
    assert clips[0].timestamp.hour == 8

    nearest = find_nearest_snap("cam4_dacha", clips[0].timestamp, root=tmp_path)
    assert nearest is not None
    assert nearest.name.startswith("20261114_115615")
