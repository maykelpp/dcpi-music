import re

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
import httpx

from middleware.rate_limit import download_rate_limit
from fastapi import Depends
from services import audio_source

router = APIRouter()
TRACK_ID_RE = re.compile(r"^[0-9]{1,20}$")
ALLOWED_QUALITIES = {96, 320}


@router.get("/{track_id}/qualities")
async def get_qualities(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")
    qualities = await audio_source.get_available_qualities(track_id)
    if not qualities:
        raise HTTPException(status_code=404, detail="Esta canción no tiene descarga habilitada por su autor")
    return {"qualities": qualities, "formats": ["mp3"]}


@router.get("/{track_id}", dependencies=[Depends(download_rate_limit)])
async def download(track_id: str = Path(...), quality: int = Query(320)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")
    if quality not in ALLOWED_QUALITIES:
        raise HTTPException(status_code=400, detail=f"Calidad no soportada. Usa: {sorted(ALLOWED_QUALITIES)}")

    info = await audio_source.get_download_url(track_id, quality)
    if not info:
        raise HTTPException(status_code=404, detail="Descarga no disponible para esta canción")

    safe_title = re.sub(r"[^\w\s-]", "", info["title"])[:80]

    async def _proxy():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("GET", info["url"]) as res:
                async for chunk in res.aiter_bytes(64 * 1024):
                    yield chunk

    return StreamingResponse(
        _proxy(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.mp3"'},
    )
