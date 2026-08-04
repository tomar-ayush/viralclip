# ViralCut AI - Automated Short-Form Viral Video Generation Platform

Production-ready, highly scalable **FastAPI** backend powering an automated 9:16 vertical short-form video generation pipeline (TikTok / YouTube Shorts / Instagram Reels).

---

## 🏗 System Architecture & Data Pipeline

```
  ┌────────────────┐     1. Get Trends     ┌───────────────────────┐
  │ Google Trends  │ ────────────────────> │ GET /api/v1/trends    │
  │ RSS / SerpAPI  │                       └───────────────────────┘
  └────────────────┘                                   │
                                                       ▼
  ┌────────────────┐   2. Generate Script  ┌───────────────────────┐
  │ OpenAI / Claude│ <──────────────────── │POST /scripts/generate │ (BYOK AES-256-GCM)
  └────────────────┘                       └───────────────────────┘
                                                       │
                                                       ▼
  ┌────────────────┐     3. Enqueue Job    ┌───────────────────────┐
  │ Redis ARQ      │ <──────────────────── │POST /videos/render    │
  │ Task Queue     │                       └───────────────────────┘
  └───────┬────────┘                                   │
          │ 4. Dispatch                                ▼
          ▼                                ┌───────────────────────┐
  ┌────────────────┐  5. PubSub Progress   │ WS /api/v1/ws/jobs/  │
  │ ARQ Worker     │ ────────────────────> │ {job_id}              │
  └───────┬────────┘                       └───────────────────────┘
          │
          ├──> 6. ElevenLabs TTS (Audio MP3 + Timestamps)
          ├──> 7. AWS S3 Upload (Audio & Assets)
          └──> 8. AWS Remotion Lambda (Render 9:16 MP4 Video)
```

---

## 📁 Directory Structure

```
sideProject/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── trends.py         # GET /api/v1/trends
│   │       │   ├── scripts.py        # POST /api/v1/scripts/generate
│   │       │   ├── videos.py         # POST /api/v1/videos/render & GET /api/v1/videos/jobs/{id}
│   │       │   ├── users.py          # POST /api/v1/user/keys & POST /api/v1/user/create
│   │       │   └── websocket.py      # WS /api/v1/ws/jobs/{job_id}
│   │       └── router.py             # Main v1 API Router
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings & Env setup
│   │   ├── db.py                     # Async PostgreSQL & SQLModel Engine
│   │   ├── redis.py                  # Redis Connection Pool & PubSub
│   │   └── security.py               # AES-256-GCM Encryption / Decryption & Key Fingerprints
│   ├── models/                       # SQLModel Database Schemas
│   │   ├── user.py                   # User model
│   │   ├── user_api_key.py           # UserAPIKey model (BYOK Provider Keys)
│   │   └── video_job.py              # VideoJob model (Render Pipeline State)
│   ├── schemas/                      # Pydantic Schemas (DTOs)
│   │   ├── user.py
│   │   ├── script.py
│   │   ├── video.py
│   │   └── trend.py
│   ├── services/                     # Business Logic & Third-party Integrations
│   │   ├── s3_service.py             # AWS S3 Uploads & Presigned URLs
│   │   ├── llm_service.py            # OpenAI Script Synthesis
│   │   ├── elevenlabs_service.py     # ElevenLabs Voice Synthesis & Alignment Timestamps
│   │   ├── remotion_service.py       # Remotion Lambda Render Dispatch
│   │   └── trends_service.py         # Google Trends RSS Parser & Redis Cache
│   ├── workers/                      # Async Task Workers
│   │   ├── arq_config.py             # Redis ARQ Worker Config
│   │   └── tasks.py                  # process_video_render_job pipeline
│   └── main.py                       # FastAPI Application Entrypoint
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔒 Security & BYOK Key Management

- Third-party API keys (OpenAI, ElevenLabs, etc.) are encrypted using **AES-256-GCM** via the `cryptography` Python library before being persisted to PostgreSQL.
- Decryption occurs transiently in-memory only during background worker execution.
- Key fingerprints (e.g. `sk-...4a8f`) are generated using SHA-256 for identification without exposing secret keys.

---

## ⚡ Quickstart & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run FastAPI Web Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 4. Run ARQ Background Render Worker
```bash
arq app.workers.arq_config.WorkerSettings
```

---

## 🚀 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/trends` | Fetch trending viral topics from Google Trends RSS (Cached in Redis) |
| `POST` | `/api/v1/user/create` | Create a new user account |
| `POST` | `/api/v1/user/keys` | Encrypt & store third-party BYOK API keys (AES-256-GCM) |
| `POST` | `/api/v1/scripts/generate` | Generate timed script schema with hooks & scene visual descriptions |
| `POST` | `/api/v1/videos/render` | Enqueue a video rendering job to Redis ARQ task queue |
| `GET` | `/api/v1/videos/jobs/{job_id}` | Poll job status & get pre-signed S3 video download URL |
| `WS` | `/api/v1/ws/jobs/{job_id}` | WebSocket stream pushing real-time progress percent (0-100%) |
