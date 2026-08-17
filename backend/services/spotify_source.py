"""
Adapter de Spotify Web API (https://developer.spotify.com/documentation/web-api).

Uso oficial vía Client Credentials Flow (auth app-a-app, sin login de
usuario). Solo da metadata + `preview_url` de 30 segundos — Spotify no
permite streaming completo ni descarga fuera de sus apps oficiales, así
que esto no intenta más que eso.

Requiere SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET (gratis, se crean en
https://developer.spotify.com/dashboard).
"""
import base64
import os
import time

import httpx

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

_token_cache = {"value": None, "expires_at": 0}


async def _get_token() -> str:
    if _token_cache["value"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["value"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Faltan SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET")

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {basic}"},
        )
        res.raise_for_status()
        data = res.json()

    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["value"]


def _to_track_summary(t: dict) -> dict:
    images = (t.get("album") or {}).get("images") or []
    cover = images[0]["url"] if images else None
    return {
        "id": t["id"],
        "title": t.get("name") or "Sin título",
        "artist": ", ".join(a["name"] for a in t.get("artists", [])) or "Desconocido",
        "album": (t.get("album") or {}).get("name"),
        "cover": cover,
        "duration": round((t.get("duration_ms") or 0) / 1000),
        "preview_url": t.get("preview_url"),  # puede ser None: no todas las canciones tienen preview
    }


async def search(query: str, limit: int = 20) -> list[dict]:
    token = await _get_token()
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            f"{API_BASE}/search",
            params={"q": query, "type": "track", "limit": min(limit, 50)},
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        data = res.json()

    tracks = data.get("tracks", {}).get("items", [])
    # Solo tiene sentido devolver canciones que sí tengan preview reproducible
    return [_to_track_summary(t) for t in tracks if t.get("preview_url")]


async def get_track_info(track_id: str) -> dict | None:
    token = await _get_token()
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(f"{API_BASE}/tracks/{track_id}", headers={"Authorization": f"Bearer {token}"})
        if res.status_code != 200:
            return None
        return _to_track_summary(res.json())
