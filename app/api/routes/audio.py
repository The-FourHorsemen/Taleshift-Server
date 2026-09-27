"""Audio / transcription HTTP routes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.asr.engine import transcribe_audio_file, transcribe_session
from app.schemas.audio import TranscriptResult, TranscribeFormMeta

router = APIRouter(tags=["audio"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
_UNPROCESSABLE = 422


@router.post(
    "/transcribe",
    response_model=TranscriptResult,
    status_code=status.HTTP_200_OK,
)
async def transcribe_upload(
    audio: UploadFile = File(..., description="Recorded audio blob"),
    storyId: str = Form(...),
    sessionId: str = Form(...),
) -> TranscriptResult:
    """
    Synchronous record→transcribe path for the Next.js app.

    Does not touch Supabase Storage — audio is posted directly and discarded
    after transcription.
    """
    try:
        meta = TranscribeFormMeta(storyId=storyId.strip(), sessionId=sessionId.strip())
    except ValidationError as exc:
        raise HTTPException(
            status_code=_UNPROCESSABLE,
            detail=f"Invalid storyId/sessionId: {exc.errors()}",
        ) from exc

    data = await audio.read()
    if not data:
        raise HTTPException(
            status_code=_UNPROCESSABLE,
            detail="Audio file is empty",
        )
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=_UNPROCESSABLE,
            detail=f"Audio file exceeds {MAX_AUDIO_BYTES // (1024 * 1024)}MB limit",
        )

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = tmp.name
    try:
        tmp.write(data)
        tmp.close()
        try:
            parsed = transcribe_audio_file(tmp_path)
        except Exception as exc:  # noqa: BLE001 — surface model failures clearly
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription model failed: {exc}",
            ) from exc
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return TranscriptResult(
        storyId=meta.storyId,
        sessionId=meta.sessionId,
        words=parsed["words"],
        fullText=parsed["fullText"],
        durationMs=parsed["durationMs"],
    )


@router.post("/audio/sessions/{session_id}/transcribe")
def transcribe_session_endpoint(session_id: str) -> dict[str, str]:
    """Transcribe a session's audio from Supabase Storage via the ASR engine."""
    try:
        text = transcribe_session(session_id)
    except Exception as exc:  # noqa: BLE001 — surface storage/ASR failures to the client
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_id": session_id, "text": text}
