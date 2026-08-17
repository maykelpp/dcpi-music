"""
Une las tres fuentes (Jamendo, Spotify, YouTube) bajo un solo esquema de
IDs prefijados ("jamendo:123", "spotify:abc", "youtube:xyz"), para que el
resto del backend no tenga que saber de cuál viene cada canción.

Capacidades reales por fuente (no se inventa nada fuera de esto):
- jamendo: reproducción completa + descarga (con metadata embebida)
- spotify: solo preview de 30s, sin descarga
- youtube: solo metadata para buscar; la reproducción la hace el frontend
  con el reproductor embebido oficial de YouTube, no hay streaming propio
"""
import asyncio

from services import jamendo_source, spotify_source, youtube_source


def _tag(track: dict, source: str) -> dict:
    track = {**track, "source": source, "id": f"{source}:{track['id']}"}
    return track


def split_id(prefixed_id: str) -> tuple[str, str]:
    source, _, raw_id = prefixed_id.partition(":")
    return source, raw_id


async def search(query: str, limit: int = 20) -> list[dict]:
    results = await asyncio.gather(
        jamendo_source.search(query, limit=8),
        _safe(spotify_source.search(query, limit=8)),
        _safe(youtube_source.search(query, limit=8)),
        return_exceptions=False,
    )
    jamendo_r, spotify_r, youtube_r = results
    combined = (
        [_tag(t, "jamendo") for t in jamendo_r]
        + [_tag(t, "spotify") for t in spotify_r]
        + [_tag(t, "youtube") for t in youtube_r]
    )
    return combined[:limit] if limit else combined


async def _safe(coro):
    """Si a una fuente le falta configurar su API key, no tumba la búsqueda entera."""
    try:
        return await coro
    except Exception as e:
        print("[sources] una fuente falló:", e)
        return []


async def get_track_info(prefixed_id: str) -> dict | None:
    source, raw_id = split_id(prefixed_id)
    if source == "jamendo":
        t = await jamendo_source.get_track_info(raw_id)
    elif source == "spotify":
        t = await spotify_source.get_track_info(raw_id)
    elif source == "youtube":
        t = await youtube_source.get_track_info(raw_id)
    else:
        return None
    return _tag(t, source) if t else None


async def get_home_feed(offset: int, limit: int = 10) -> list[dict]:
    results = await jamendo_source.get_home_feed(offset, limit)
    return [_tag(t, "jamendo") for t in results]


async def get_radio_mix(seed_prefixed_id: str, offset: int, limit: int = 10) -> list[dict]:
    source, raw_id = split_id(seed_prefixed_id)
    if source != "jamendo":
        # Solo Jamendo tiene un mecanismo de "más como esta" implementado por ahora
        return await get_home_feed(offset, limit)
    results = await jamendo_source.get_radio_mix(raw_id, offset, limit)
    return [_tag(t, "jamendo") for t in results]
