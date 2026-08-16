import os
import re

from fastapi import Header, HTTPException

from middleware.telegram_auth import verify_telegram_init_data

_GUEST_ID_RE = re.compile(r"^[a-zA-Z0-9-]{8,64}$")


async def get_user_id(
    x_telegram_init_data: str = Header(None),
    x_guest_id: str = Header(None),
) -> str:
    """
    Devuelve un identificador único de usuario, sin importar si entra desde
    Telegram o desde un navegador normal:
    - Si manda initData de Telegram válido, usa "tg:<id_de_telegram>".
    - Si no, usa "guest:<uuid>" generado y guardado por el propio frontend.
    Así history/favorites funcionan igual en ambos casos.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if x_telegram_init_data and bot_token:
        user = verify_telegram_init_data(x_telegram_init_data, bot_token)
        if user:
            return f"tg:{user['id']}"

    if x_guest_id and _GUEST_ID_RE.match(x_guest_id):
        return f"guest:{x_guest_id}"

    raise HTTPException(status_code=400, detail="Falta identificación de usuario")
