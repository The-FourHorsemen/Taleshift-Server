"""
ASR engine — wraps a Hugging Face Whisper pipeline and pulls session
audio from Supabase.

To swap models, change MODEL_ID (or set the TALESHIFT_ASR_MODEL_ID
env var) — nothing else in this file needs to change.
"""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from typing import Any

from transformers import pipeline

from app.db.client import get_supabase_client

# --- single point of change for the active ASR model ---------------
MODEL_ID = os.getenv(
    "TALESHIFT_ASR_MODEL_ID",
    "dsfsi-anv/whisper-large-v3-turbo-anv-zul",
)

# Supabase Storage bucket where session audio is temporarily kept
AUDIO_BUCKET = os.getenv("TALESHIFT_AUDIO_BUCKET", "session-audio")


@lru_cache(maxsize=1)
def get_asr_pipeline():
    """Load the Whisper ASR model once per process; shared by all callers."""
    return pipeline("automatic-speech-recognition", model=MODEL_ID)


# Backwards-compatible alias used by older call sites.
_get_pipeline = get_asr_pipeline


def _fetch_audio_path(session_id: str) -> str:
    """
    Look up the audio file for a reading session and download it
    from Supabase Storage into a local temp file. Returns the temp
    file path.

    Assumes a `reading_sessions` table with an `audio_path` column
    pointing at the object's path in the storage bucket — adjust the
    table/column names to match your actual schema.
    """
    supabase = get_supabase_client()

    row = (
        supabase.table("reading_sessions")
        .select("audio_path")
        .eq("id", session_id)
        .single()
        .execute()
    )
    audio_path = row.data["audio_path"]

    audio_bytes = supabase.storage.from_(AUDIO_BUCKET).download(audio_path)

    suffix = os.path.splitext(audio_path)[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(audio_bytes)
    tmp.close()
    return tmp.name


def _words_from_pipeline_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Map Whisper pipeline chunks to the shared TranscriptResult word shape.

    Limitation: the Hugging Face Whisper ASR pipeline does not expose a real
    per-word confidence score, so ``confidence`` is always the placeholder 1.0.
    """
    words: list[dict[str, Any]] = []
    for chunk in result.get("chunks") or []:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        timestamp = chunk.get("timestamp") or (None, None)
        start_s, end_s = timestamp[0], timestamp[1]
        start_ms = int(round((start_s or 0.0) * 1000))
        end_ms = int(round((end_s if end_s is not None else (start_s or 0.0)) * 1000))
        words.append(
            {
                "text": text,
                "startMs": start_ms,
                "endMs": end_ms,
                "confidence": 1.0,
            }
        )
    return words


def transcribe_audio_file(audio_path: str) -> dict[str, Any]:
    """
    Run word-level ASR on a local audio file.

    Returns dict keys: words, fullText, durationMs (no story/session ids).
    """
    asr = get_asr_pipeline()
    result = asr(audio_path, return_timestamps="word")
    words = _words_from_pipeline_result(result)
    full_text = (result.get("text") or "").strip()
    if not full_text and words:
        full_text = " ".join(w["text"] for w in words)
    duration_ms = max((w["endMs"] for w in words), default=0)
    return {
        "words": words,
        "fullText": full_text,
        "durationMs": duration_ms,
    }


def transcribe_session(session_id: str) -> str:
    """
    Fetch a session's audio from the DB/storage, transcribe it, and
    return the text. The temp file is deleted afterwards either way —
    audio shouldn't outlive the transcription step.
    """
    audio_path = _fetch_audio_path(session_id)
    try:
        asr = get_asr_pipeline()
        result = asr(audio_path, return_timestamps=True)
        return result["text"]
    finally:
        os.remove(audio_path)
