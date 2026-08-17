"""
Adapter de Jamendo (una de tres fuentes — ver sources.py para el dispatcher) (https://api.jamendo.com/v3.0/).

Plataforma real de música con licencias libres/Creative Commons: los
artistas suben su música específicamente para que se pueda transmitir y
descargar vía API. A diferencia de YouTube, no bloquea peticiones
automatizadas ni requiere cookies — es una API pública pensada para esto.

Catálogo: independiente/indie, no artistas mainstream. Es la contrapartida
de no depender de scraping/yt-dlp.

Requiere JAMENDO_CLIENT_ID (gratis en https://devportal.jamendo.com/).
"""
import os
from typing import Optional

import httpx

JAMENDO_BASE = "https://api.jamendo.com/v3.0"

# Géneros reales soportados por el sistema de tags de Jamendo — se rota
# entre ellos para el feed inicial (antes de tener una canción de referencia).
GENRE_SEEDS = [
    "pop", "rock", "electronic", "hiphop", "chillout",
    "jazz", "latin", "reggae", "folk", "classical",
]


def _client_id() -> str:
    cid = os.getenv("JAMENDO_CLIENT_ID")
    if not cid:
        raise RuntimeError("Falta JAMENDO_CLIENT_ID en las variables de entorno")
    return cid


def _to_track_summary(t: dict) -> dict:
    return {
        "id": str(t.get("id")),
        "title": t.get("name") or "Sin título",
        "artist": t.get("artist_name") or "Desconocido",
        "album": t.get("album_name") or None,
        "cover": t.get("image") or t.get("album_image") or None,
        "duration": int(t.get("duration") or 0),
        # internos, no se exponen tal cual al frontend pero se usan en streaming/descarga:
        "_audio_url": t.get("audio"),
        "_download_url": t.get("audiodownload"),
        "_download_allowed": bool(t.get("audiodownload_allowed")),
        "_genres": ((t.get("musicinfo") or {}).get("tags") or {}).get("genres") or [],
    }


async def _get(path: str, params: dict) -> dict:
    params = {**params, "client_id": _client_id(), "format": "json"}
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(f"{JAMENDO_BASE}{path}", params=params)
        res.raise_for_status()
        return res.json()


async def search(query: str, limit: int = 20) -> list[dict]:
    data = await _get("/tracks/", {
        "namesearch": query, "limit": limit, "include": "musicinfo",
        "audioformat": "mp32", "order": "relevance",
    })
    return [_to_track_summary(t) for t in data.get("results", [])]


async def get_track_info(track_id: str) -> Optional[dict]:
    data = await _get("/tracks/", {"id": track_id, "include": "musicinfo", "audioformat": "mp32"})
    results = data.get("results", [])
    return _to_track_summary(results[0]) if results else None


async def get_available_qualities(track_id: str) -> list[int]:
    """
    Jamendo solo ofrece dos códecs de verdad: ~96kbps (mp31) y ~320kbps
    (mp32). No se muestra nada que la fuente no confirme.
    """
    track = await get_track_info(track_id)
    if not track or not track["_download_allowed"]:
        return []
    return [96, 320]


def _quality_to_format(quality: int) -> str:
    return "mp32" if quality >= 200 else "mp31"


async def get_stream_url(track_id: str) -> Optional[str]:
    track = await get_track_info(track_id)
    return track["_audio_url"] if track else None


async def get_download_url(track_id: str, quality: int = 320) -> Optional[dict]:
    data = await _get("/tracks/", {
        "id": track_id, "audioformat": _quality_to_format(quality),
    })
    results = data.get("results", [])
    if not results:
        return None
    t = results[0]
    if not t.get("audiodownload_allowed"):
        return None
    return {"url": t.get("audiodownload"), "title": t.get("name") or "cancion"}


# ===== Feed / recomendaciones =====

async def get_home_feed(offset: int, limit: int = 10) -> list[dict]:
    genre = GENRE_SEEDS[(offset // limit) % len(GENRE_SEEDS)]
    data = await _get("/tracks/", {
        "tags": genre, "limit": limit, "order": "popularity_month",
        "include": "musicinfo", "audioformat": "mp32",
    })
    return [_to_track_summary(t) for t in data.get("results", [])]


async def get_radio_mix(seed_track_id: str, offset: int, limit: int = 10) -> list[dict]:
    """Recomendaciones basadas en los géneros reales de la canción semilla."""
    seed = await get_track_info(seed_track_id)
    if not seed or not seed["_genres"]:
        return await get_home_feed(offset, limit)

    genre = seed["_genres"][0]
    data = await _get("/tracks/", {
        "tags": genre, "limit": limit, "offset": offset,
        "order": "popularity_month", "include": "musicinfo", "audioformat": "mp32",
    })
    results = [_to_track_summary(t) for t in data.get("results", [])]
    # evita recomendarse a sí misma como primer resultado
    return [r for r in results if r["id"] != seed_track_id]
