"""Spawn ffmpeg to remux RTSP → MPEG-TS and pump bytes onto a WebSocket."""

from __future__ import annotations

import os
import select
import subprocess
import time

# How often we poll the WS for client close while waiting on ffmpeg stdout.
_RECV_POLL_S = 0.25
_CHUNK = 64 * 1024
# No stdout within this window → treat as missing recording / unreachable RTSP.
FIRST_BYTE_TIMEOUT_S = 8.0


def stream_rtsp_mpegts(
    ws,
    rtsp_url: str,
    *,
    logger=None,
    first_byte_timeout_s: float = FIRST_BYTE_TIMEOUT_S,
) -> None:
    """Block until the WebSocket closes or ffmpeg exits; always kills ffmpeg.

    If no MPEG-TS bytes arrive within ``first_byte_timeout_s``, send a JSON
    ``{error, code: no_recording}`` frame so the UI can show a clear message.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-an",
        "-c:v",
        "copy",
        "-f",
        "mpegts",
        "pipe:1",
    ]
    proc = None
    try:
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # New process group so we can kill children on teardown.
                start_new_session=True,
            )
        except FileNotFoundError:
            if logger is not None:
                logger.error("ffmpeg not found on PATH")
            try:
                ws.send({"error": "ffmpeg not available", "code": "ffmpeg_missing"})
            except Exception:
                pass
            return

        stdout = proc.stdout
        assert stdout is not None
        fd = stdout.fileno()
        got_byte = False
        deadline = time.monotonic() + max(0.5, float(first_byte_timeout_s))
        while ws.open and proc.poll() is None:
            wait = _RECV_POLL_S
            if not got_byte:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    try:
                        ws.send(
                            {
                                "error": "No recording or stream data for this time",
                                "code": "no_recording",
                            }
                        )
                    except Exception:
                        pass
                    if logger is not None:
                        logger.info("ffmpeg produced no data within %.1fs", first_byte_timeout_s)
                    break
                wait = min(wait, remaining)
            ready, _, _ = select.select([fd], [], [], wait)
            if ready:
                chunk = os.read(fd, _CHUNK)
                if not chunk:
                    break
                got_byte = True
                try:
                    ws.send(chunk)
                except Exception:
                    break
            # Brief poll for client close / control frames when idle or between chunks.
            try:
                ws.recv(timeout=0.05)
            except Exception:
                break
            if not ws.open:
                break

        # ffmpeg exited before any payload (auth / empty track / bad URL).
        if not got_byte and ws.open:
            try:
                ws.send(
                    {
                        "error": "No recording or stream data for this time",
                        "code": "no_recording",
                    }
                )
            except Exception:
                pass

        if proc.poll() is None:
            try:
                proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
    finally:
        _kill_proc(proc, logger=logger)


def _kill_proc(proc: subprocess.Popen | None, *, logger=None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        _drain_stderr(proc)
        return
    try:
        os.killpg(proc.pid, 15)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except Exception:
            pass
    deadline = time.time() + 2.0
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.05)
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, 9)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=1)
        except Exception:
            pass
    _drain_stderr(proc, logger=logger)


def _drain_stderr(proc: subprocess.Popen, *, logger=None) -> None:
    err = proc.stderr
    if err is None:
        return
    try:
        data = err.read()
    except Exception:
        return
    if data and logger is not None:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            logger.debug("ffmpeg stderr: %s", text[-500:])
