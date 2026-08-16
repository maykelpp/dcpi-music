"""
Adapter de fuente de audio.

Búsqueda/metadata y extracción real de audio, todo vía el binario `yt-dlp`
(no requiere API key). Aislado aquí para poder sustituir la fuente después
sin tocar routers.
"""
import asyncio
import json
import os
import subprocess
from typing import Optional

# YouTube bloquea/pide verificación ("Sign in to confirm you're not a bot")
# con más frecuencia a peticiones desde IPs de datacenter. Distintos
# "clientes" (formas de identificarse) reciben distinto trato — se prueban
# en cascada hasta que uno funcione, en vez de depender de uno solo.
_CLIENT_FALLBACKS = ["android", "ios", "tv_embedded", "web_embedded", "web"]

# Si se configura un archivo de cookies (exportado de una cuenta de YouTube
# logueada), se usa como último recurso — es lo único 100% confiable contra
# este bloqueo, pero requiere que el usuario lo genere y suba manualmente.
_COOKIES_FILE = os.getenv("YT_COOKIES_FILE")  # ej: ./cookies.txt


def _base_args(client: str) -> list[str]:
    args = ["--extractor-args", f"youtube:player_client={client}", "--no-warnings"]
    if _COOKIES_FILE and os.path.exists(_COOKIES_FILE):
        args += ["--cookies", _COOKIES_FILE]
    return args


async def _run_json(url: str) -> tuple[dict, str]:
    """Corre `yt-dlp -J` probando cada cliente hasta que uno no falle por bloqueo.
    Devuelve (datos, cliente_que_funcionó)."""
    last_err = ""
    for client in _CLIENT_FALLBACKS:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-J", *_base_args(client), url,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode == 0:
            return json.loads(out), client
        last_err = err.decode(errors="ignore")
        print(f"[audio_source] cliente '{client}' falló: {last_err[:200]}")
    raise RuntimeError(last_err or "yt-dlp falló con todos los clientes disponibles")


def _to_track_summary(entry: dict) -> dict:
    duration = entry.get("duration") or 0
    thumbnails = entry.get("thumbnails") or []
    cover = thumbnails[-1]["url"] if thumbnails else entry.get("thumbnail")
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "artist": entry.get("channel") or entry.get("uploader") or "Desconocido",
        "album": None,
        "cover": cover,
        "duration": int(duration),
    }


async def search(query: str, limit: int = 20) -> list[dict]:
    data, _client = await _run_json(f"ytsearch{limit * 2}:{query}")
    entries = data.get("entries") or []
    results = []
    for e in entries:
        duration = e.get("duration") or 0
        if 0 < duration < 15 * 60:
            results.append(_to_track_summary(e))
        if len(results) >= limit:
            break
    return results


async def get_track_info(video_id: str) -> Optional[dict]:
    try:
        entry, _client = await _run_json(f"https://www.youtube.com/watch?v={video_id}")
    except RuntimeError:
        return None
    return _to_track_summary(entry)


async def get_working_client(video_id: str) -> Optional[str]:
    """Descubre qué cliente sirve para este video, para reutilizarlo en streaming/descarga."""
    try:
        _entry, client = await _run_json(f"https://www.youtube.com/watch?v={video_id}")
        return client
    except RuntimeError:
        return None


async def get_available_qualities(video_id: str) -> list[int]:
    info, _client = await _run_json(f"https://www.youtube.com/watch?v={video_id}")
    audio_formats = [f for f in info.get("formats", []) if f.get("acodec") and f.get("acodec") != "none"]
    max_abr = max([f.get("abr") or 0 for f in audio_formats], default=0)

    offered = [128, 192, 256, 320]
    available = [q for q in offered if max_abr >= q - 16]
    return available or [128]


def stream_audio_process(video_id: str, fmt: str = "mp3", quality: int = 192, client: str = "android") -> subprocess.Popen:
    """Devuelve el proceso yt-dlp con stdout en modo pipe (streaming, sin guardar en disco)."""
    args = [
        "yt-dlp",
        "-f", "bestaudio",
        *_base_args(client),
        "-x",
        "--audio-format", fmt,
        "--audio-quality", f"{quality}K",
        "-o", "-",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


CLIENT_FALLBACKS = _CLIENT_FALLBACKS
