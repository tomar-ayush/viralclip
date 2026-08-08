# ── ViralClip FFmpeg Render Service ──────────────────────────────────────
# Works on: HuggingFace Spaces, Render.com, Koyeb, Railway, any Docker host
# Base image has Python + ffmpeg preinstalled (saves 200MB vs building ffmpeg)
FROM python:3.11-slim

# Install ffmpeg + fonts (needed for ASS subtitle rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

# HuggingFace Spaces runs as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# HuggingFace default port is 7860
# Render.com / Koyeb use PORT env var (set below as fallback)
EXPOSE 7860

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
