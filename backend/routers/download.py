import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse

from middleware.rate_limit import download_rate_limit
from routers.stream import _iter_process_stdout
from services import audio_source

router = APIRouter()
TRACK_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{6,20}$")
ALLOWED_FORMATS = {"mp3", "m4a"}
ALLOWED_QUALITIES = {128, 192, 256, 320}


@router.get("/{track_id}/qualities")
async def get_qualities(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")
    try:
        qualities = await audio_source.get_available_qualities(track_id)
        return {"qualities": qualities, "formats": sorted(ALLOWED_FORMATS)}
    except Exception as e:
        print("[download:qualities]", e)
        raise HTTPException(status_code=502, detail="No se pudieron comprobar las calidades disponibles")


@router.get("/{track_id}", dependencies=[Depends(download_rate_limit)])
async def download(
    track_id: str = Path(...),
    format: str = Query("mp3"),
    quality: int = Query(192),
):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")
    if format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Formato no soportado. Usa: {', '.join(ALLOWED_FORMATS)}")
    if quality not in ALLOWED_QUALITIES:
        raise HTTPException(status_code=400, detail=f"Calidad no soportada. Usa: {sorted(ALLOWED_QUALITIES)}")

    track = await audio_source.get_track_info(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Canción no encontrada")

    safe_title = re.sub(r"[^\w\s-]", "", track["title"])[:80]
    proc = audio_source.stream_audio_process(track_id, format, quality)
    media_type = "audio/mp4" if format == "m4a" else "audio/mpeg"

    return StreamingResponse(
        _iter_process_stdout(proc),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.{format}"'},
    )
