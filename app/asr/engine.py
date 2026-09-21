"""
ASR engine — wraps a Hugging Face Whisper pipeline and pulls session
audio from Supabase.

To swap models, change MODEL_ID (or set the TALESHIFT_ASR_MODEL_ID
env var) — nothing else in this file needs to change.
"""

import os
import tempfile
from functools import lru_cache

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
def _get_pipeline():
    """Load the model once per process, reuse on every call."""
    return pipeline("automatic-speech-recognition", model=MODEL_ID)


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


def transcribe_session(session_id: str) -> str:
    """
    Fetch a session's audio from the DB/storage, transcribe it, and
    return the text. The temp file is deleted afterwards either way —
    audio shouldn't outlive the transcription step.
    """
    audio_path = _fetch_audio_path(session_id)
    try:
        asr = _get_pipeline()
        result = asr(audio_path, return_timestamps=True)
        return result["text"]
    finally:
        os.remove(audio_path)