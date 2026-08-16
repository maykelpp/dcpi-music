import re

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import RedirectResponse

from services import audio_source

router = APIRouter()
TRACK_ID_RE = re.compile(r"^[0-9]{1,20}$")


@router.get("/{track_id}")
async def stream(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    url = await audio_source.get_stream_url(track_id)
    if not url:
        raise HTTPException(status_code=404, detail="Canción no encontrada")

    # Jamendo sirve el audio directo desde su propio CDN — redirigimos en
    # vez de hacer proxy, así no cargamos ancho de banda de nuestro server.
    return RedirectResponse(url=url)
