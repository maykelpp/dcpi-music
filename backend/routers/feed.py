import re

from fastapi import APIRouter, HTTPException, Query

from services import audio_source

router = APIRouter()
TRACK_ID_RE = re.compile(r"^[0-9]{1,20}$")


@router.get("")
async def get_feed(
    seed: str = Query(None, description="ID de la última canción reproducida, para recomendaciones reales"),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=25),
):
    if seed and not TRACK_ID_RE.match(seed):
        raise HTTPException(status_code=400, detail="ID de semilla inválido")

    try:
        if seed:
            results = await audio_source.get_radio_mix(seed, offset, limit)
        else:
            results = await audio_source.get_home_feed(offset, limit)
        return {"results": results, "offset": offset, "seed": seed}
    except Exception as e:
        print("[feed]", e)
        raise HTTPException(status_code=502, detail="No se pudo cargar el feed")
