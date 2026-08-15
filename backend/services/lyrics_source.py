"""
Adapter de letras — mismo comportamiento que la versión Node:
1) lrclib.net (gratis, sin auth) para letras sincronizadas (LRC).
2) Genius como fallback: solo metadata + enlace externo (Genius no permite
   servir el texto completo de la letra vía su API pública).
No se inventan letras ni timestamps en ningún punto.
"""
import os
import re
import httpx

LRCLIB_BASE = "https://lrclib.net/api"
GENIUS_BASE = "https://api.genius.com"

_LRC_LINE_RE = re.compile(r"\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\](.*)")


def parse_lrc(lrc_text: str) -> list[dict]:
    if not lrc_text:
        return []
    lines = []
    for mm, ss, ms, text in _LRC_LINE_RE.findall(lrc_text):
        time = int(mm) * 60 + int(ss) + (int(ms) / (100 if len(ms) == 2 else 1000) if ms else 0)
        trimmed = text.strip()
        if trimmed:
            lines.append({"time": time, "text": trimmed})
    return sorted(lines, key=lambda l: l["time"])


async def get_lyrics(title: str, artist: str, duration: int | None = None) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. lrclib
        try:
            params = {"track_name": title, "artist_name": artist}
            if duration:
                params["duration"] = str(duration)
            res = await client.get(f"{LRCLIB_BASE}/get", params=params)
            if res.status_code == 200:
                data = res.json()
                if data.get("syncedLyrics"):
                    return {"synced": True, "lines": parse_lrc(data["syncedLyrics"]), "source": "lrclib"}
                if data.get("plainLyrics"):
                    return {"synced": False, "text": data["plainLyrics"], "source": "lrclib"}
        except Exception:
            pass

        # 2. Genius (fallback, solo texto/enlace)
        genius_key = os.getenv("GENIUS_API_KEY")
        if genius_key:
            try:
                res = await client.get(
                    f"{GENIUS_BASE}/search",
                    params={"q": f"{title} {artist}"},
                    headers={"Authorization": f"Bearer {genius_key}"},
                )
                if res.status_code == 200:
                    hits = res.json().get("response", {}).get("hits", [])
                    if hits:
                        hit = hits[0]["result"]
                        return {
                            "synced": False,
                            "text": None,
                            "externalUrl": hit.get("url"),
                            "source": "genius",
                            "note": "Letras no sincronizadas disponibles en Genius (enlace externo).",
                        }
            except Exception:
                pass

    return {"synced": False, "text": None, "source": None, "note": "Letras no disponibles para esta canción."}
