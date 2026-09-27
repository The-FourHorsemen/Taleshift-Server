"""
Application settings loaded from environment / .env.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    taleshift_asr_model_id: str = Field(
        default="dsfsi-anv/whisper-large-v3-turbo-anv-zul",
        validation_alias="TALESHIFT_ASR_MODEL_ID",
    )
    taleshift_audio_bucket: str = Field(
        default="session-audio",
        validation_alias="TALESHIFT_AUDIO_BUCKET",
    )
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_key: str = Field(..., validation_alias="SUPABASE_KEY")
    # Comma-separated string in env (e.g. "http://localhost:3000,http://localhost:5173")
    allowed_origins: str = Field(default="*", validation_alias="ALLOWED_ORIGINS")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        parts = [p.strip() for p in self.allowed_origins.split(",") if p.strip()]
        return parts or ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
