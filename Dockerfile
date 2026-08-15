FROM python:3.12-slim

# ffmpeg: necesario para que yt-dlp extraiga/convierta audio (mp3/m4a)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir -U yt-dlp

COPY backend ./backend
COPY frontend ./frontend

WORKDIR /app/backend

# Render inyecta $PORT — hay que escuchar ahí, no en un puerto fijo
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-3000}
