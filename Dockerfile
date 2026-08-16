FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY frontend ./frontend

WORKDIR /app/backend

# Render inyecta $PORT — hay que escuchar ahí, no en un puerto fijo
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-3000}
