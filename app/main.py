from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle events handler.
    """
    print("[Startup] Initializing database tables...")
    try:
        await init_db()
        print("[Startup] Database tables initialized successfully.")
    except Exception as e:
        print(f"[Startup Warning] Could not connect to PostgreSQL DB ({e}). Running app in standalone/degraded mode.")
    
    yield
    print("[Shutdown] Cleaning up platform backend services...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated Short-Form Viral Video Generation Platform Backend API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for frontend web application & preview tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }
