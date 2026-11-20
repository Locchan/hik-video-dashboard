from __future__ import annotations

from hvd.streaming.dvr import (
    _isapi_debug_body,
    build_rtsp_url,
    list_dvrs_with_channels,
    parse_streaming_dvr_config,
    query_stream_params,
    resolve_dvr,
)


def _entries(*pairs):
    return [{"name": k, "value": v, "group_read": 1} for k, v in pairs]


def test_parse_streaming_dvr_config_and_channel_names():
    entries = _entries(
        ("STREAMING_DVR_1_NAME", "Yard"),
        ("STREAMING_DVR_1_HTTP_ADDR", "192.0.2.10"),
        ("STREAMING_DVR_1_RTSP_ADDR", "192.0.2.11"),
        ("STREAMING_DVR_1_USERNAME", "admin"),
        ("STREAMING_DVR_1_PASSWORD", "secret"),
        ("STREAMING_DVR_1_CH_101_NAME", "Gate"),
        # HTTP only — not registered.
        ("STREAMING_DVR_2_HTTP_ADDR", "192.0.2.20"),
        ("UNRELATED", "x"),
    )
    dvrs = parse_streaming_dvr_config(entries)
    assert set(dvrs) == {"1"}
    assert dvrs["1"]["name"] == "Yard"
    assert dvrs["1"]["http_addr"] == "192.0.2.10"
    assert dvrs["1"]["rtsp_addr"] == "192.0.2.11"
    assert dvrs["1"]["username"] == "admin"
    assert dvrs["1"]["channel_names"]["101"] == "Gate"


def test_list_dvrs_with_channels_public_shape():
    entries = _entries(
        ("STREAMING_DVR_1_NAME", "Yard"),
        ("STREAMING_DVR_1_HTTP_ADDR", "192.0.2.10"),
        ("STREAMING_DVR_1_RTSP_ADDR", "192.0.2.11"),
        ("STREAMING_DVR_1_USERNAME", "admin"),
        ("STREAMING_DVR_1_PASSWORD", "secret"),
        ("STREAMING_DVR_1_CH_101_NAME", "Gate"),
    )

    def fake_fetch(addr, user, password):
        assert addr == "192.0.2.10"
        assert user == "admin"
        assert password == "secret"
        return ["101", "102"]

    out = list_dvrs_with_channels(entries, fetch_fn=fake_fetch)
    assert out == {
        "DVR_1": {
            "NAME": "Yard",
            "CHANNELS": {
                "101": {"NAME": "Gate"},
                "102": {"NAME": "102"},
            },
        }
    }
    # Secrets never appear in the public payload.
    blob = str(out)
    assert "secret" not in blob
    assert "admin" not in blob
    assert "192.0.2.10" not in blob
    assert "192.0.2.11" not in blob


def test_build_rtsp_url_and_resolve():
    url = build_rtsp_url("192.0.2.10", "admin", "p@ss", "101")
    assert url == "rtsp://admin:p%40ss@192.0.2.10:554/Streaming/Channels/101"
    url2 = build_rtsp_url("rtsp://192.0.2.10:8554", "u", "p", "201")
    assert url2 == "rtsp://u:p@192.0.2.10:8554/Streaming/Channels/201"
    entries = _entries(
        ("STREAMING_DVR_9_HTTP_ADDR", "192.0.2.8"),
        ("STREAMING_DVR_9_RTSP_ADDR", "192.0.2.9"),
        ("STREAMING_DVR_9_USERNAME", "u"),
        ("STREAMING_DVR_9_PASSWORD", "p"),
    )
    assert resolve_dvr(entries, "9")["rtsp_addr"] == "192.0.2.9"
    assert resolve_dvr(entries, "9")["http_addr"] == "192.0.2.8"
    assert resolve_dvr(entries, "DVR_9")["rtsp_addr"] == "192.0.2.9"
    assert resolve_dvr(entries, "missing") is None


def test_query_stream_params():
    assert query_stream_params("/streaming/stream?dvr=1&channel=101") == ("1", "101")
    assert query_stream_params("/streaming/stream?dvr=DVR_2&channel=201") == ("2", "201")
    assert query_stream_params("/streaming/stream") == (None, None)


def test_isapi_debug_body_truncates():
    body = ("x" * 100).encode()
    out = _isapi_debug_body(body, limit=20)
    assert out.startswith("x" * 20)
    assert "truncated" in out


def test_list_dvrs_logs_fetch_failure_at_debug():
    entries = _entries(
        ("STREAMING_DVR_1_HTTP_ADDR", "192.0.2.10"),
        ("STREAMING_DVR_1_RTSP_ADDR", "192.0.2.11"),
        ("STREAMING_DVR_1_USERNAME", "admin"),
        ("STREAMING_DVR_1_PASSWORD", "secret"),
    )
    messages: list[str] = []

    class _Log:
        def debug(self, msg, *args):
            messages.append(msg % args if args else msg)

    def boom(addr, user, password):
        raise RuntimeError("ISAPI HTTP 401")

    out = list_dvrs_with_channels(entries, fetch_fn=boom, logger=_Log())
    assert out["DVR_1"]["CHANNELS"] == {}
    assert any("ISAPI channel list failed" in m for m in messages)
