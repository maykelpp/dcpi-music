import re

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import RedirectResponse

from services import jamendo_source, spotify_source, sources

router = APIRouter()
TRACK_ID_RE = re.compile(r"^(jamendo|spotify|youtube):[a-zA-Z0-9_-]{1,64}$")


@router.get("/{track_id:path}")
async def stream(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    source, raw_id = sources.split_id(track_id)

    if source == "jamendo":
        url = await jamendo_source.get_stream_url(raw_id)
        if not url:
            raise HTTPException(status_code=404, detail="Canción no encontrada")
        return RedirectResponse(url=url)

    if source == "spotify":
        track = await spotify_source.get_track_info(raw_id)
        if not track or not track.get("preview_url"):
            raise HTTPException(status_code=404, detail="Esta canción no tiene preview disponible en Spotify")
        return RedirectResponse(url=track["preview_url"])

    if source == "youtube":
        raise HTTPException(
            status_code=409,
            detail="Las canciones de YouTube se reproducen con el reproductor embebido oficial, no por streaming propio",
        )

    raise HTTPException(status_code=400, detail="Fuente desconocida")
