import re

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse

from services import audio_source

router = APIRouter()
TRACK_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{6,20}$")


def _iter_process_stdout(proc):
    try:
        while True:
            chunk = proc.stdout.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        if proc.poll() is None:
            proc.kill()


@router.get("/{track_id}")
async def stream(track_id: str = Path(...)):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    client = await audio_source.get_working_client(track_id)
    if not client:
        raise HTTPException(status_code=502, detail="No se pudo acceder al audio de esta canción")

    proc = audio_source.stream_audio_process(track_id, "mp3", 192, client=client)
    return StreamingResponse(_iter_process_stdout(proc), media_type="audio/mpeg")
