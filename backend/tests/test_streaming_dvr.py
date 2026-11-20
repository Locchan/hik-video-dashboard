from __future__ import annotations

from datetime import datetime

import pytest

from hvd.streaming.dvr import (
    _build_cm_search_xml,
    _isapi_debug_body,
    _parse_cm_search_result,
    build_rtsp_url,
    fetch_recording_bounds,
    find_recording_cover,
    list_dvrs_with_channels,
    parse_playback_start,
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
    start = datetime(2024, 6, 1, 12, 30, 0)
    play = build_rtsp_url(
        "192.0.2.10", "admin", "p", "101", start=start, end=datetime(2024, 6, 1, 13, 0, 0)
    )
    assert play == (
        "rtsp://admin:p@192.0.2.10:554/Streaming/tracks/101/"
        "?starttime=20240601T123000Z&endtime=20240601T130000Z"
    )
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


def test_parse_playback_start():
    assert parse_playback_start(None) is None
    assert parse_playback_start("") is None
    assert parse_playback_start("2024-06-01T12:30") == datetime(2024, 6, 1, 12, 30)
    assert parse_playback_start("2024-06-01T12:30:45") == datetime(2024, 6, 1, 12, 30, 45)
    assert parse_playback_start("2024-06-01T12:30:45Z") == datetime(2024, 6, 1, 12, 30, 45)
    with pytest.raises(ValueError):
        parse_playback_start("not-a-time")


def test_query_stream_params():
    assert query_stream_params("/streaming/stream?dvr=1&channel=101") == (
        "1",
        "101",
        None,
    )
    assert query_stream_params(
        "/streaming/stream?dvr=DVR_2&channel=201&start=2024-06-01T12:30"
    ) == ("2", "201", "2024-06-01T12:30")
    assert query_stream_params("/streaming/stream") == (None, None, None)


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


def test_parse_cm_search_result_bounds():
    xml = b"""<?xml version="1.0"?>
    <CMSearchResult>
      <responseStatusStrg>OK</responseStatusStrg>
      <matchList>
        <searchMatchItem>
          <timeSpan>
            <startTime>2024-06-01T10:00:00Z</startTime>
            <endTime>2024-06-01T11:00:00Z</endTime>
          </timeSpan>
        </searchMatchItem>
        <searchMatchItem>
          <timeSpan>
            <startTime>2024-06-03T08:15:00Z</startTime>
            <endTime>2024-06-03T09:00:00Z</endTime>
          </timeSpan>
        </searchMatchItem>
      </matchList>
    </CMSearchResult>
    """
    status, spans = _parse_cm_search_result(xml)
    assert status == "OK"
    assert len(spans) == 2
    assert spans[0][0] == datetime(2024, 6, 1, 10, 0, 0)
    assert spans[1][1] == datetime(2024, 6, 3, 9, 0, 0)


def test_build_cm_search_xml_uses_postion_typo():
    raw = _build_cm_search_xml(
        "101",
        datetime(2024, 1, 1, 0, 0, 0),
        datetime(2024, 1, 2, 0, 0, 0),
        offset=40,
        max_results=100,
    ).decode()
    assert "<searchResultPostion>40</searchResultPostion>" in raw
    assert "<trackID>101</trackID>" in raw
    # NVR-local wall time (no Z) so ContentMgmt matches datetime-local / RTSP local.
    assert "2024-01-01T00:00:00" in raw
    assert "2024-01-01T00:00:00Z" not in raw


def test_find_recording_cover_hit_and_miss(monkeypatch):
    monkeypatch.setattr(
        "hvd.streaming.dvr._isapi_request",
        lambda *a, **k: b"""<?xml version="1.0"?><CMSearchResult>
          <responseStatusStrg>OK</responseStatusStrg>
          <matchList>
            <searchMatchItem><timeSpan>
              <startTime>2024-06-01T10:00:00</startTime>
              <endTime>2024-06-01T11:00:00</endTime>
            </timeSpan></searchMatchItem>
          </matchList>
        </CMSearchResult>""",
    )
    hit = find_recording_cover(
        "192.0.2.10", "u", "p", "101", datetime(2024, 6, 1, 10, 30, 0)
    )
    assert hit == datetime(2024, 6, 1, 10, 30, 0)
    miss = find_recording_cover(
        "192.0.2.10", "u", "p", "101", datetime(2024, 6, 1, 12, 0, 0)
    )
    assert miss is None


def test_fetch_recording_bounds_min_max(monkeypatch):
    pages = [
        b"""<?xml version="1.0"?><CMSearchResult>
          <responseStatusStrg>MORE</responseStatusStrg>
          <matchList>
            <searchMatchItem><timeSpan>
              <startTime>2024-05-01T12:00:00Z</startTime>
              <endTime>2024-05-01T13:00:00Z</endTime>
            </timeSpan></searchMatchItem>
          </matchList>
        </CMSearchResult>""",
        b"""<?xml version="1.0"?><CMSearchResult>
          <responseStatusStrg>OK</responseStatusStrg>
          <matchList>
            <searchMatchItem><timeSpan>
              <startTime>2024-06-10T18:30:00Z</startTime>
              <endTime>2024-06-10T19:00:00Z</endTime>
            </timeSpan></searchMatchItem>
          </matchList>
        </CMSearchResult>""",
    ]
    calls = {"n": 0}

    def fake_request(*args, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        return pages[i]

    monkeypatch.setattr("hvd.streaming.dvr._isapi_request", fake_request)
    out = fetch_recording_bounds(
        "192.0.2.10",
        "u",
        "p",
        "101",
        now=datetime(2024, 6, 15, 12, 0, 0),
        page_size=1,
    )
    assert out["min"] == "2024-05-01T12:00"
    assert out["max"] == "2024-06-10T19:00"
    assert out["days"] == ["2024-05-01", "2024-06-10"]
    assert calls["n"] == 2


def test_days_from_spans_fills_multi_day():
    from hvd.streaming.dvr import _days_from_spans

    days = _days_from_spans(
        [
            (datetime(2024, 6, 1, 22, 0, 0), datetime(2024, 6, 3, 2, 0, 0)),
        ]
    )
    assert days == ["2024-06-01", "2024-06-02", "2024-06-03"]


def test_fetch_recording_bounds_no_matches(monkeypatch):
    monkeypatch.setattr(
        "hvd.streaming.dvr._isapi_request",
        lambda *a, **k: b"""<?xml version="1.0"?><CMSearchResult>
          <responseStatusStrg>NO MATCHES</responseStatusStrg>
        </CMSearchResult>""",
    )
    assert (
        fetch_recording_bounds(
            "192.0.2.10", "u", "p", "101", now=datetime(2024, 6, 15, 12, 0, 0)
        )
        is None
    )
