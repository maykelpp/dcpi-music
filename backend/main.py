import os

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from middleware.rate_limit import api_rate_limit
from routers import download, favorites, history, lyrics, search, stream, track, telegram_webhook

app = FastAPI(title="DCPI Music Backend")

allowed_origin = os.getenv("WEBAPP_URL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin] if allowed_origin else [],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _on_startup():
    await telegram_webhook.register_webhook()


# Rutas públicas (solo consultan el catálogo, sin datos de usuario)
app.include_router(search.router, prefix="/api/search", dependencies=[Depends(api_rate_limit)])
app.include_router(track.router, prefix="/api/track", dependencies=[Depends(api_rate_limit)])
app.include_router(lyrics.router, prefix="/api/lyrics", dependencies=[Depends(api_rate_limit)])
app.include_router(stream.router, prefix="/api/stream")
app.include_router(download.router, prefix="/api/download", dependencies=[Depends(api_rate_limit)])

# Rutas que dependen del usuario (auth de Telegram se valida dentro de cada router)
app.include_router(history.router, prefix="/api/history", dependencies=[Depends(api_rate_limit)])
app.include_router(favorites.router, prefix="/api/favorites", dependencies=[Depends(api_rate_limit)])

# Webhook de Telegram — recibe los updates del bot directamente (sin polling)
app.include_router(telegram_webhook.router, prefix="/telegram/webhook")


@app.get("/health")
async def health():
    return {"ok": True, "service": "dcpi-music-backend-python"}


# Frontend estático — se monta al final para no chocar con /api/* ni /health.
# Con html=True, "/" sirve frontend/index.html automáticamente.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
