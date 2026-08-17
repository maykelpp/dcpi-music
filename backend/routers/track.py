import re

from fastapi import APIRouter, HTTPException, Path

from services import sources

router = APIRouter()
TRACK_ID_RE = re.compile(r"^(jamendo|spotify|youtube):[a-zA-Z0-9_-]{1,64}$")


@router.get("/{track_id:path}")
async def get_track(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")
    try:
        track = await sources.get_track_info(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Canción no encontrada")
        return track
    except HTTPException:
        raise
    except Exception as e:
        print("[track]", e)
        raise HTTPException(status_code=502, detail="No se pudo obtener la información de la canción")
