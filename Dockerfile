# Python:3.11-slim + CPU torch + transformers ASR API
FROM python:3.11-slim

WORKDIR /app

# ffmpeg: decode browser recordings (webm/ogg/mp3) for the Whisper pipeline
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Platforms (Fly, Railway, Render) inject PORT; default 8000 for local Docker.
ENV PORT=8000
# HF cache — on Fly this is overridden to the mounted volume via fly.toml [env].
ENV HF_HOME=/root/.cache/huggingface

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
