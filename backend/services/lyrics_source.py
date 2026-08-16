"""
Adapter de letras.

1) lrclib.net (https://lrclib.net/docs) — API pública, sin auth, devuelve
   letras sincronizadas en formato LRC.
2) Genius API — solo texto plano, SIN timestamps. Se usa únicamente como
   fallback cuando lrclib no tiene nada, y solo se devuelve el enlace
   externo (Genius no permite servir el texto completo vía su API pública).

No se inventan letras ni timestamps en ningún punto de este archivo.
"""
import os
import re

import httpx

LRCLIB_BASE = "https://lrclib.net/api"
GENIUS_BASE = "https://api.genius.com"

_TAG_RE = re.compile(r"\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\]")


def parse_lrc(lrc_text: str) -> list[dict]:
    """
    Parsea LRC línea por línea, soportando:
    - milisegundos de 2 o 3 dígitos, o ausentes
    - líneas de metadata ([ti:], [ar:], etc.) — se ignoran, no son timestamps
    - múltiples timestamps en una misma línea (coros repetidos, "enhanced LRC")
    - CRLF y LF
    - líneas fuera de orden en el archivo (se ordenan al final)
    """
    if not lrc_text:
        return []
    lines = []
    for raw_line in lrc_text.splitlines():
        tags = list(_TAG_RE.finditer(raw_line))
        if not tags:
            continue
        text = raw_line[tags[-1].end():].strip()
        if not text:
            continue
        for m in tags:
            mm, ss, ms = m.group(1), m.group(2), m.group(3)
            time = int(mm) * 60 + int(ss) + (int(ms) / (100 if ms and len(ms) == 2 else 1000) if ms else 0)
            lines.append({"time": time, "text": text})
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
        except Exception as e:
            print("[lyrics_source] lrclib falló:", e)

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
            except Exception as e:
                print("[lyrics_source] genius falló:", e)

    return {"synced": False, "text": None, "source": None, "note": "Letras no disponibles para esta canción."}
