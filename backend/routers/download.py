import os
import re
import tempfile

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, APIC

from middleware.rate_limit import download_rate_limit
from services import jamendo_source, sources

router = APIRouter()
TRACK_ID_RE = re.compile(r"^(jamendo|spotify|youtube):[a-zA-Z0-9_-]{1,64}$")
ALLOWED_QUALITIES = {96, 320}


@router.get("/{track_id:path}/qualities")
async def get_qualities(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    source, raw_id = sources.split_id(track_id)
    if source != "jamendo":
        raise HTTPException(status_code=409, detail="Solo las canciones de Jamendo se pueden descargar")

    qualities = await jamendo_source.get_available_qualities(raw_id)
    if not qualities:
        raise HTTPException(status_code=404, detail="Esta canción no tiene descarga habilitada por su autor")
    return {"qualities": qualities, "formats": ["mp3"]}


async def _fetch_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.get(url)
        res.raise_for_status()
        return res.content


def _embed_metadata(mp3_path: str, title: str, artist: str, album: str | None, cover_bytes: bytes | None):
    """Embebe título/artista/álbum/portada como tags ID3, igual que un mp3 'de verdad'."""
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.setall("TIT2", [TIT2(encoding=3, text=title)])
    tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
    if album:
        tags.setall("TALB", [TALB(encoding=3, text=album)])
    if cover_bytes:
        tags.setall("APIC", [APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_bytes)])

    tags.save(mp3_path)


@router.get("/{track_id:path}", dependencies=[Depends(download_rate_limit)])
async def download(track_id: str = Path(...), quality: int = Query(320)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    source, raw_id = sources.split_id(track_id)
    if source != "jamendo":
        raise HTTPException(status_code=409, detail="Solo las canciones de Jamendo se pueden descargar")
    if quality not in ALLOWED_QUALITIES:
        raise HTTPException(status_code=400, detail=f"Calidad no soportada. Usa: {sorted(ALLOWED_QUALITIES)}")

    info = await jamendo_source.get_download_url(raw_id, quality)
    if not info:
        raise HTTPException(status_code=404, detail="Descarga no disponible para esta canción")

    track = await jamendo_source.get_track_info(raw_id)
    if not track:
        raise HTTPException(status_code=404, detail="Canción no encontrada")

    audio_bytes = await _fetch_bytes(info["url"])
    cover_bytes = None
    if track.get("cover"):
        try:
            cover_bytes = await _fetch_bytes(track["cover"])
        except Exception:
            cover_bytes = None  # si falla la portada, igual se entrega el audio

    safe_title = re.sub(r"[^\w\s-]", "", info["title"])[:80] or "cancion"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3", prefix="dcpi_")
    os.close(tmp_fd)
    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)

    _embed_metadata(tmp_path, track["title"], track["artist"], track.get("album"), cover_bytes)

    return FileResponse(
        tmp_path,
        media_type="audio/mpeg",
        filename=f"{safe_title}.mp3",
        background=BackgroundTask(lambda: os.remove(tmp_path) if os.path.exists(tmp_path) else None),
    )
