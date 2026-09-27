"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.audio import router as audio_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Taleshift Server")

_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Browsers reject credentials with wildcard origins.
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
