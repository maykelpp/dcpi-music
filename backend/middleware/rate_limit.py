"""
Rate limiter simple por IP, en memoria (ventana deslizante). Suficiente para
un solo proceso en Termux/VPS; si se escala a múltiples workers, migrar a
Redis.
"""
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)


def _check(request: Request, window_seconds: int, max_requests: int, bucket_prefix: str = ""):
    ip = request.client.host if request.client else "unknown"
    key = f"{bucket_prefix}:{ip}"
    now = time.time()

    _buckets[key] = [t for t in _buckets[key] if now - t < window_seconds]
    if len(_buckets[key]) >= max_requests:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Espera un momento.")

    _buckets[key].append(now)


async def api_rate_limit(request: Request):
    window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))
    max_req = int(os.getenv("RATE_LIMIT_MAX", 30))
    _check(request, window, max_req, "api")


async def download_rate_limit(request: Request):
    _check(request, 300, 10, "download")
