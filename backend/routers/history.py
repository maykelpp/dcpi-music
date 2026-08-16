from fastapi import APIRouter, Depends

from db.init import db
from middleware.identity import get_user_id

router = APIRouter()


@router.get("")
async def get_history(user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    rows = db().execute(
        "SELECT track_id, title, artist, cover_url, played_at FROM history "
        "WHERE telegram_id = ? ORDER BY played_at DESC LIMIT 100",
        (telegram_id,),
    ).fetchall()
    return {"history": [dict(r) for r in rows]}


@router.post("", status_code=201)
async def add_history(payload: dict, user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    track_id = payload.get("track_id")
    title = payload.get("title")
    artist = payload.get("artist")
    cover_url = payload.get("cover_url")

    if not track_id or not title or not artist:
        return {"error": "Faltan datos de la canción"}, 400

    db().execute(
        "INSERT INTO history (telegram_id, track_id, title, artist, cover_url) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, str(track_id)[:50], str(title)[:200], str(artist)[:200], (str(cover_url)[:500] if cover_url else None)),
    )
    db().commit()
    return {"ok": True}


@router.delete("")
async def clear_history(user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    db().execute("DELETE FROM history WHERE telegram_id = ?", (telegram_id,))
    db().commit()
    return {"ok": True}
