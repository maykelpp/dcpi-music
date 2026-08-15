import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

MAX_AGE_SECONDS = 86400  # 24h


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(pairs.get("auth_date", 0))
    if time.time() - auth_date > MAX_AGE_SECONDS:
        return None

    user_raw = pairs.get("user")
    return json.loads(user_raw) if user_raw else None


async def telegram_auth(x_telegram_init_data: str = Header(None)) -> dict:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not x_telegram_init_data or not bot_token:
        raise HTTPException(status_code=401, detail="Falta autenticación de Telegram")

    user = verify_telegram_init_data(x_telegram_init_data, bot_token)
    if not user:
        raise HTTPException(status_code=401, detail="initData inválido o expirado")

    return user
