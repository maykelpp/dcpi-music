"""
Webhook de Telegram: en vez de un proceso aparte haciendo polling (que no
cabe en el plan gratuito de un solo servicio web), Telegram nos manda los
updates por HTTP a esta ruta. Vive dentro del mismo proceso que la API,
así que todo corre en un único servicio/URL.
"""
import os

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter()

TELEGRAM_API = "https://api.telegram.org"


def _bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN")
    return token


async def send_webapp_button(chat_id: int, text: str):
    webapp_url = os.getenv("WEBAPP_URL")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[{"text": "🔎 Abrir DCPI Music", "web_app": {"url": webapp_url}}]]
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/bot{_bot_token()}/sendMessage", json=payload)


@router.post("")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    # Verifica que el request venga realmente de Telegram (secret configurado al registrar el webhook)
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=401, detail="Secreto de webhook inválido")

    update = await request.json()
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = message.get("chat", {}).get("id")

    if chat_id and text.startswith("/start"):
        await send_webapp_button(chat_id, "🎵 *DCPI Music*\n\nTu reproductor musical dentro de Telegram, con letras sincronizadas.")
    elif chat_id and text.startswith("/music"):
        await send_webapp_button(chat_id, "🎵 Abrir DCPI Music")

    return {"ok": True}


async def register_webhook():
    """Le dice a Telegram dónde mandar los updates. Se llama al arrancar la app."""
    webapp_url = os.getenv("WEBAPP_URL")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not webapp_url or webapp_url == "https://tu-dominio.com":
        print("[telegram] WEBAPP_URL no configurada aún, no se registra el webhook")
        return

    payload = {"url": f"{webapp_url}/telegram/webhook"}
    if secret:
        payload["secret_token"] = secret

    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(f"{TELEGRAM_API}/bot{_bot_token()}/setWebhook", json=payload)
        print("[telegram] setWebhook:", res.json())
