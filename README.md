# ViralCut AI - Automated Short-Form Viral Video Generation Platform

Production-ready, highly scalable **FastAPI** backend powering an automated 9:16 vertical short-form video generation pipeline (TikTok / YouTube Shorts / Instagram Reels), built with a **Domain-Driven (Feature-Based) Architecture**.

---

## 📁 Domain-Driven Directory Structure

```
sideProject/
├── app/
│   ├── common/                       # Cross-cutting platform infrastructure
│   │   ├── config.py                 # Pydantic Settings & Env configuration
│   │   ├── db.py                     # Async PostgreSQL SQLModel engine
│   │   ├── redis.py                  # Redis connection pool & PubSub publisher
│   │   └── security.py               # AES-256-GCM Encryption/Decryption & Fingerprinting
│   │
│   ├── users/                        # User management & BYOK Security domain
│   │   ├── model.py                  # User & UserAPIKey DB schemas
│   │   ├── schema.py                 # User & API Key request/response DTOs
│   │   └── router.py                 # POST /api/v1/user/create & POST /api/v1/user/keys
│   │
│   ├── trends/                       # Viral Trends domain
│   │   ├── schema.py                 # TrendItem & TrendsResponse DTOs
│   │   ├── service.py                # Google Trends RSS Parser & Redis Cache
│   │   └── router.py                 # GET /api/v1/trends
│   │
│   ├── scripts/                      # AI Script Synthesis domain
│   │   ├── schema.py                 # Timed script & scene DTOs
│   │   ├── service.py                # OpenAI LLM script synthesis service
│   │   └── router.py                 # POST /api/v1/scripts/generate
│   │
│   ├── videos/                       # Video Generation & Worker domain
│   │   ├── model.py                  # VideoJob DB schema & JobStatus Enum
│   │   ├── schema.py                 # Video render request & job status DTOs
│   │   ├── service.py                # ElevenLabs TTS & Remotion Lambda integration
│   │   ├── tasks.py                  # ARQ process_video_render_job background worker
│   │   └── router.py                 # Render, status, and WebSocket endpoints
│   │
│   ├── storage/                      # Cloud Storage domain
│   │   └── service.py                # AWS S3 Uploads & Presigned URLs
│   │
│   ├── workers.py                    # ARQ Worker Configuration Settings
│   └── main.py                       # Main FastAPI Application Entrypoint
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

## ⚡ Quickstart & Commands

### 1. Run FastAPI Web Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`

### 2. Run ARQ Background Render Worker
```bash
arq app.workers.WorkerSettings
```
### 3.

