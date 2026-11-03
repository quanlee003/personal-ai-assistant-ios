from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from deepgram_service import transcribe_audio

app = FastAPI(title="Personal AI Assistant API")

MAX_AUDIO_BYTES = 10 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024


class AudioInspectionResponse(BaseModel):
    status: str
    filename: str | None
    content_type: str | None
    size_bytes: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/audio/inspect", response_model=AudioInspectionResponse)
async def inspect_audio(
    file: Annotated[UploadFile, File()],
) -> AudioInspectionResponse:
    try:
        size_bytes = 0

        while chunk := await file.read(READ_CHUNK_BYTES):
            size_bytes += len(chunk)

            if size_bytes > MAX_AUDIO_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="File vượt giới hạn 10 MiB.",
                )

        if size_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="File không có dữ liệu.",
            )

        return AudioInspectionResponse(
            status="received",
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=size_bytes,
        )
    finally:
        await file.close()


class TranscriptionResponse(BaseModel):
    text: str
    engine: str


@app.post("/audio/transcribe", response_model=TranscriptionResponse)
async def transcribe_recording(
    file: Annotated[UploadFile, File()],
) -> TranscriptionResponse:
    try:
        audio = await file.read(MAX_AUDIO_BYTES + 1)

        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File vượt giới hạn 10 MiB.",
            )

        if not audio:
            raise HTTPException(
                status_code=400,
                detail="File không có dữ liệu.",
            )

        text = await transcribe_audio(audio)

        return TranscriptionResponse(
            text=text,
            engine="deepgram",
        )
    finally:
        await file.close()