"""Tests for ASR HTTP endpoints (Whisper pipeline is mocked — never loaded)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Settings are required at app import time.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from app.api.routes.audio import MAX_AUDIO_BYTES  # noqa: E402
from app.schemas.audio import TranscriptResult  # noqa: E402

TRANSCRIPT_RESULT_KEYS = {"storyId", "sessionId", "words", "fullText", "durationMs"}
WORD_KEYS = {"text", "startMs", "endMs", "confidence"}

FAKE_PIPELINE_RESULT = {
    "text": " hello world",
    "chunks": [
        {"text": " hello", "timestamp": (0.0, 0.5)},
        {"text": " world", "timestamp": (0.5, 1.2)},
    ],
}


def _fake_pipeline():
    """Stand-in for the Hugging Face ASR pipeline callable."""

    def _call(audio_path, return_timestamps=None):
        assert return_timestamps == "word"
        assert isinstance(audio_path, str)
        return FAKE_PIPELINE_RESULT

    return _call


@pytest.fixture
def client():
    with patch("app.asr.engine.get_asr_pipeline", side_effect=_fake_pipeline):
        from app.main import app

        with TestClient(app) as test_client:
            yield test_client


def _post_transcribe(
    client: TestClient,
    *,
    audio: bytes = b"fake-audio-bytes",
    filename: str = "clip.wav",
    story_id: str = "story-1",
    session_id: str = "session-9",
):
    return client.post(
        "/transcribe",
        data={"storyId": story_id, "sessionId": session_id},
        files={"audio": (filename, audio, "audio/wav")},
    )


def test_transcribe_response_matches_transcript_result_contract(client: TestClient):
    response = _post_transcribe(client)

    assert response.status_code == 200
    payload = response.json()

    assert set(payload.keys()) == TRANSCRIPT_RESULT_KEYS
    assert "accuracyScore" not in payload
    assert "fluencyScore" not in payload

    # Validates types/shape against the shared pydantic contract.
    result = TranscriptResult.model_validate(payload)
    assert result.storyId == "story-1"
    assert result.sessionId == "session-9"
    assert result.fullText == "hello world"
    assert result.durationMs == 1200
    assert len(result.words) == 2
    assert result.words[0].model_dump() == {
        "text": "hello",
        "startMs": 0,
        "endMs": 500,
        "confidence": 1.0,
    }
    assert result.words[1].model_dump() == {
        "text": "world",
        "startMs": 500,
        "endMs": 1200,
        "confidence": 1.0,
    }
    for word in payload["words"]:
        assert set(word.keys()) == WORD_KEYS


def test_transcribe_rejects_empty_audio(client: TestClient):
    response = _post_transcribe(client, audio=b"")

    assert response.status_code == 422
    assert response.json()["detail"] == "Audio file is empty"


def test_transcribe_rejects_oversized_audio(client: TestClient):
    response = _post_transcribe(client, audio=b"x" * (MAX_AUDIO_BYTES + 1))

    assert response.status_code == 422
    assert "10MB" in response.json()["detail"]


def test_transcribe_rejects_missing_form_fields(client: TestClient):
    response = client.post(
        "/transcribe",
        files={"audio": ("clip.wav", b"fake-audio-bytes", "audio/wav")},
    )

    assert response.status_code == 422


def test_transcribe_model_failure_returns_500(client: TestClient):
    def boom_pipeline():
        def _call(audio_path, return_timestamps=None):
            raise RuntimeError("cuda OOM (simulated)")

        return _call

    with patch("app.asr.engine.get_asr_pipeline", side_effect=boom_pipeline):
        response = _post_transcribe(client)

    assert response.status_code == 500
    assert "Transcription model failed" in response.json()["detail"]
