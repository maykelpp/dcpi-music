import asyncio

import pytest
from fastapi import HTTPException

from services import sources, youtube_source, spotify_source, jamendo_source
from routers import track as track_router
from routers import stream as stream_router
from routers import feed as feed_router


def test_01_split_prefixed_id():
    assert sources.split_id("jamendo:12345") == ("jamendo", "12345")


def test_02_youtube_summary_from_search_payload():
    result = youtube_source._to_track_summary({
        "id": {"kind": "youtube#video", "videoId": "abc123"},
        "snippet": {"title": "Tema", "channelTitle": "Canal", "thumbnails": {}}
    })
    assert result["id"] == "abc123"
    assert result["title"] == "Tema"


def test_03_youtube_summary_rejects_missing_video_id():
    assert youtube_source._to_track_summary({"id": {"kind": "youtube#channel"}}) is None


def test_04_youtube_duration_parser():
    assert youtube_source._parse_iso8601_duration("PT1H2M3S") == 3723
    assert youtube_source._parse_iso8601_duration("invalid") == 0


def test_05_spotify_summary_keeps_preview_url():
    result = spotify_source._to_track_summary({
        "id": "sp123", "name": "Preview", "artists": [{"name": "Artista"}],
        "album": {"name": "Disco", "images": []},
        "duration_ms": 30000, "preview_url": "https://audio.example/preview.mp3"
    })
    assert result["preview_url"].endswith("preview.mp3")
    assert result["duration"] == 30


def test_06_jamendo_summary_exposes_download_capability():
    result = jamendo_source._to_track_summary({
        "id": "55", "name": "Local", "artist_name": "Artista",
        "audiodownload_allowed": True, "audio": "https://audio.example/song.mp3"
    })
    assert result["id"] == "55"
    assert result["_download_allowed"] is True
    assert result["_audio_url"].endswith("song.mp3")


def test_07_track_route_rejects_invalid_id():
    with pytest.raises(HTTPException) as err:
        asyncio.run(track_router.get_track("bad id"))
    assert err.value.status_code == 400


def test_08_track_route_returns_metadata(monkeypatch):
    async def fake(_track_id):
        return {"id": "jamendo:55", "title": "Tema"}
    monkeypatch.setattr(track_router.sources, "get_track_info", fake)
    result = asyncio.run(track_router.get_track("jamendo:55"))
    assert result["title"] == "Tema"


def test_09_track_route_returns_404_when_missing(monkeypatch):
    async def fake(_track_id):
        return None
    monkeypatch.setattr(track_router.sources, "get_track_info", fake)
    with pytest.raises(HTTPException) as err:
        asyncio.run(track_router.get_track("jamendo:999"))
    assert err.value.status_code == 404


def test_10_stream_jamendo_redirect(monkeypatch):
    async def fake(_raw_id):
        return "https://audio.example/jamendo.mp3"
    monkeypatch.setattr(stream_router.jamendo_source, "get_stream_url", fake)
    result = asyncio.run(stream_router.stream("jamendo:55"))
    assert result.status_code == 307
    assert result.headers["location"].endswith("jamendo.mp3")


def test_11_stream_spotify_redirect(monkeypatch):
    async def fake(_raw_id):
        return {"preview_url": "https://audio.example/spotify.mp3"}
    monkeypatch.setattr(stream_router.spotify_source, "get_track_info", fake)
    result = asyncio.run(stream_router.stream("spotify:sp123"))
    assert result.status_code == 307
    assert result.headers["location"].endswith("spotify.mp3")


def test_12_stream_youtube_is_not_extracted():
    with pytest.raises(HTTPException) as err:
        asyncio.run(stream_router.stream("youtube:abc123"))
    assert err.value.status_code == 409


def test_13_feed_rejects_invalid_seed():
    with pytest.raises(HTTPException) as err:
        asyncio.run(feed_router.get_feed(seed="not-valid", offset=0, limit=10))
    assert err.value.status_code == 400


def test_14_feed_loads_default_recommendations(monkeypatch):
    async def fake(_offset, _limit):
        return [{"id": "jamendo:1"}]
    monkeypatch.setattr(feed_router.sources, "get_home_feed", fake)
    result = asyncio.run(feed_router.get_feed(seed=None, offset=0, limit=10))
    assert result["results"][0]["id"] == "jamendo:1"


def test_15_feed_loads_seeded_recommendations(monkeypatch):
    async def fake(_seed, _offset, _limit):
        return [{"id": "jamendo:2"}]
    monkeypatch.setattr(feed_router.sources, "get_radio_mix", fake)
    result = asyncio.run(feed_router.get_feed(seed="jamendo:1", offset=10, limit=5))
    assert result["results"][0]["id"] == "jamendo:2"
    assert result["seed"] == "jamendo:1"
