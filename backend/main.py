import asyncio
import os
import traceback

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from middleware.rate_limit import api_rate_limit
from routers import download, favorites, history, lyrics, search, stream, track, telegram_webhook

app = FastAPI(title="DCPI Music Backend")

# CORS abierto: esta ya es una web pública normal, no solo una WebApp de
# Telegram con un único origen fijo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ===== Manejo global de errores =====
# Cualquier excepción no capturada en una ruta cae aquí en vez de tumbar el
# proceso o devolver un HTML feo — siempre JSON, siempre con código 500,
# y queda registrada en los logs para poder depurarla.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"[unhandled] {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": "Error interno del servidor"})


# ===== Anti-hibernación (plan Free de Render) =====
# Render duerme el servicio tras ~15 min sin tráfico entrante. Esta tarea de
# fondo se hace un "self-ping" cada 10 minutos a su propia URL pública, lo
# que cuenta como tráfico real y evita que llegue a dormirse. No es 100%
# infalible (si Render lo suspende por otro motivo, este loop también se
# detiene y hay que esperar el primer request real), pero cubre la mayoría
# de los casos de inactividad normal.
async def _keep_alive_loop():
    await asyncio.sleep(30)  # deja que la app termine de arrancar primero
    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url or webapp_url == "https://tu-dominio.com":
        print("[keep-alive] WEBAPP_URL no configurada, self-ping desactivado")
        return

    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            try:
                res = await client.get(f"{webapp_url}/health")
                print(f"[keep-alive] ping ok: {res.status_code}")
            except Exception as e:
                print(f"[keep-alive] ping falló: {e}")
            await asyncio.sleep(10 * 60)  # cada 10 minutos, antes de los 15 min de límite


@app.on_event("startup")
async def _on_startup():
    await telegram_webhook.register_webhook()
    asyncio.create_task(_keep_alive_loop())


# Rutas públicas (solo consultan el catálogo, sin datos de usuario)
app.include_router(search.router, prefix="/api/search", dependencies=[Depends(api_rate_limit)])
app.include_router(track.router, prefix="/api/track", dependencies=[Depends(api_rate_limit)])
app.include_router(lyrics.router, prefix="/api/lyrics", dependencies=[Depends(api_rate_limit)])
app.include_router(stream.router, prefix="/api/stream")
app.include_router(download.router, prefix="/api/download", dependencies=[Depends(api_rate_limit)])

# Historial/favoritos: funcionan con Telegram O con un ID de invitado del navegador
app.include_router(history.router, prefix="/api/history", dependencies=[Depends(api_rate_limit)])
app.include_router(favorites.router, prefix="/api/favorites", dependencies=[Depends(api_rate_limit)])

# Webhook de Telegram — opcional, no bloquea el funcionamiento de la web si no se usa
app.include_router(telegram_webhook.router, prefix="/telegram/webhook")


@app.get("/health")
async def health():
    return {"ok": True, "service": "dcpi-music-backend-python"}


# Frontend estático — se monta al final para no chocar con /api/* ni /health.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
