import re

from fastapi import APIRouter, HTTPException, Path, Request
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
async def stream(track_id: str = Path(...), request: Request = None):
    if not TRACK_ID_RE.match(track_id):
        raise HTTPException(status_code=400, detail="ID de canción inválido")

    proc = audio_source.stream_audio_process(track_id, "mp3", 192)
    return StreamingResponse(_iter_process_stdout(proc), media_type="audio/mpeg")
