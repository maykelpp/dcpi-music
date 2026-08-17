import re

from fastapi import APIRouter, HTTPException, Query

from services import sources

router = APIRouter()
TRACK_ID_RE = re.compile(r"^(jamendo|spotify|youtube):[a-zA-Z0-9_-]{1,64}$")


@router.get("")
async def get_feed(
    seed: str = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=25),
):
    if seed and not TRACK_ID_RE.match(seed):
        raise HTTPException(status_code=400, detail="ID de semilla inválido")
    try:
        if seed:
            results = await sources.get_radio_mix(seed, offset, limit)
        else:
            results = await sources.get_home_feed(offset, limit)
        return {"results": results, "offset": offset, "seed": seed}
    except Exception as e:
        print("[feed]", e)
        raise HTTPException(status_code=502, detail="No se pudo cargar el feed")
