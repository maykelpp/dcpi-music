from fastapi import APIRouter, HTTPException, Query

from services import audio_source

router = APIRouter()


@router.get("")
async def search(q: str = Query(..., min_length=2, max_length=100)):
    try:
        results = await audio_source.search(q.strip(), 20)
        return {"results": results}
    except Exception as e:
        print("[search]", e)
        raise HTTPException(status_code=502, detail="No se pudo completar la búsqueda")
