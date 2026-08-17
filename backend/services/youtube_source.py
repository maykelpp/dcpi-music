"""
Adapter de YouTube — usa la API oficial de Google (YouTube Data API v3),
NO scraping ni yt-dlp. Solo trae metadata para poder buscar y mostrar
resultados; la reproducción se hace en el frontend con el reproductor
embebido oficial de YouTube (IFrame Player API), nunca extrayendo audio.
Así se respetan sus Términos de Servicio en ambos sentidos.

Requiere YOUTUBE_API_KEY (gratis, se crea en Google Cloud Console →
habilitar "YouTube Data API v3" → Credenciales → API Key).
Tiene cuota diaria gratuita (10,000 unidades/día; una búsqueda cuesta 100).
"""
import os

import httpx

API_BASE = "https://www.googleapis.com/youtube/v3"


def _api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("Falta YOUTUBE_API_KEY")
    return key


def _to_track_summary(item: dict, duration_seconds: int = 0) -> dict:
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId") or item.get("id")
    thumbs = snippet.get("thumbnails", {})
    cover = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    return {
        "id": video_id,
        "title": snippet.get("title") or "Sin título",
        "artist": snippet.get("channelTitle") or "Desconocido",
        "album": None,
        "cover": cover,
        "duration": duration_seconds,  # se completa con /videos si se necesita exacto
    }


async def search(query: str, limit: int = 20) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            f"{API_BASE}/search",
            params={
                "key": _api_key(), "q": query, "part": "snippet",
                "type": "video", "videoCategoryId": "10",  # 10 = Música
                "maxResults": min(limit, 50),
            },
        )
        res.raise_for_status()
        data = res.json()

    return [_to_track_summary(item) for item in data.get("items", [])]


async def get_track_info(video_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            f"{API_BASE}/videos",
            params={"key": _api_key(), "id": video_id, "part": "snippet,contentDetails"},
        )
        res.raise_for_status()
        items = res.json().get("items", [])

    if not items:
        return None
    item = items[0]
    duration = _parse_iso8601_duration(item.get("contentDetails", {}).get("duration", "PT0S"))
    return _to_track_summary(item, duration)


def _parse_iso8601_duration(s: str) -> int:
    """Convierte 'PT3M45S' a segundos, sin depender de librerías extra."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m:
        return 0
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se
