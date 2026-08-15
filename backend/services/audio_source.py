"""
Adapter de fuente de audio.

Búsqueda/metadata y extracción real de audio, todo vía el binario `yt-dlp`
(no requiere API key). Aislado aquí para poder sustituir la fuente después
sin tocar routers.
"""
import asyncio
import json
import subprocess
from typing import Optional

# YouTube suele bloquear/pedir verificación al cliente "web" cuando la
# petición viene de una IP de datacenter (como Render). Forzar el cliente
# "android" evita ese chequeo en la mayoría de los casos.
_ANTIBLOCK_ARGS = ["--extractor-args", "youtube:player_client=android,web"]


def _to_track_summary(entry: dict) -> dict:
    duration = entry.get("duration") or 0
    thumbnails = entry.get("thumbnails") or []
    cover = thumbnails[-1]["url"] if thumbnails else entry.get("thumbnail")
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "artist": entry.get("channel") or entry.get("uploader") or "Desconocido",
        "album": None,  # yt-dlp/YouTube no expone álbum de forma fiable
        "cover": cover,
        "duration": int(duration),
    }


async def search(query: str, limit: int = 20) -> list[dict]:
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        f"ytsearch{limit * 2}:{query}",
        "-J", "--flat-playlist", "--no-warnings", *_ANTIBLOCK_ARGS,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        print("[audio_source.search] yt-dlp stderr:", err.decode(errors="ignore"))
        raise RuntimeError(err.decode(errors="ignore") or "yt-dlp falló al buscar")

    data = json.loads(out)
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
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-J", "--no-warnings", *_ANTIBLOCK_ARGS, f"https://www.youtube.com/watch?v={video_id}",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        print("[audio_source.get_track_info] yt-dlp stderr:", err.decode(errors="ignore"))
        return None
    entry = json.loads(out)
    return _to_track_summary(entry)


async def get_available_qualities(video_id: str) -> list[int]:
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-J", "--no-warnings", *_ANTIBLOCK_ARGS, f"https://www.youtube.com/watch?v={video_id}",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        print("[audio_source.get_available_qualities] yt-dlp stderr:", err.decode(errors="ignore"))
        raise RuntimeError(err.decode(errors="ignore") or "yt-dlp falló al listar formatos")

    info = json.loads(out)
    audio_formats = [f for f in info.get("formats", []) if f.get("acodec") and f.get("acodec") != "none"]
    max_abr = max([f.get("abr") or 0 for f in audio_formats], default=0)

    offered = [128, 192, 256, 320]
    available = [q for q in offered if max_abr >= q - 16]
    return available or [128]


def stream_audio_process(video_id: str, fmt: str = "mp3", quality: int = 192) -> subprocess.Popen:
    """Devuelve el proceso yt-dlp con stdout en modo pipe (streaming, sin guardar en disco)."""
    args = [
        "yt-dlp",
        "-f", "bestaudio",
        "--no-warnings",
        *_ANTIBLOCK_ARGS,
        "-x",
        "--audio-format", fmt,
        "--audio-quality", f"{quality}K",
        "-o", "-",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
