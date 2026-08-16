from fastapi import APIRouter, Depends, Path

from db.init import db
from middleware.identity import get_user_id

router = APIRouter()


@router.get("")
async def get_favorites(user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    rows = db().execute(
        "SELECT track_id, title, artist, album, cover_url, duration, added_at FROM favorites "
        "WHERE telegram_id = ? ORDER BY added_at DESC",
        (telegram_id,),
    ).fetchall()
    return {"favorites": [dict(r) for r in rows]}


@router.post("", status_code=201)
async def add_favorite(payload: dict, user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    track_id = payload.get("track_id")
    title = payload.get("title")
    artist = payload.get("artist")

    if not track_id or not title or not artist:
        return {"error": "Faltan datos de la canción"}, 400

    db().execute(
        """INSERT INTO favorites (telegram_id, track_id, title, artist, album, cover_url, duration)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(telegram_id, track_id) DO NOTHING""",
        (
            telegram_id, str(track_id)[:50], str(title)[:200], str(artist)[:200],
            (str(payload.get("album"))[:200] if payload.get("album") else None),
            (str(payload.get("cover_url"))[:500] if payload.get("cover_url") else None),
            payload.get("duration"),
        ),
    )
    db().commit()
    return {"ok": True}


@router.delete("/{track_id}")
async def remove_favorite(track_id: str = Path(...), user_id: str = Depends(get_user_id)):
    telegram_id = user_id
    db().execute("DELETE FROM favorites WHERE telegram_id = ? AND track_id = ?", (telegram_id, track_id))
    db().commit()
    return {"ok": True}
