"""Pydantic models for the realtime record→transcribe contract."""

from pydantic import BaseModel, Field


class TranscriptWord(BaseModel):
    text: str
    startMs: int
    endMs: int
    # Placeholder 1.0 when Whisper does not expose per-word confidence.
    confidence: float = Field(..., ge=0.0, le=1.0)


class TranscriptResult(BaseModel):
    """Shared shape with the Next.js ``TranscriptResult`` type."""

    storyId: str
    sessionId: str
    words: list[TranscriptWord]
    fullText: str
    durationMs: int


class TranscribeFormMeta(BaseModel):
    """Non-file fields for ``POST /transcribe`` multipart requests."""

    storyId: str = Field(..., min_length=1)
    sessionId: str = Field(..., min_length=1)
