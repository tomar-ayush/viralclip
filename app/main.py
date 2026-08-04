from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import settings
from app.common.db import init_db
from app.scripts import scripts_router
from app.trends import trends_router
from app.users import users_router
from app.videos import videos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Initializing database models...")
    try:
        await init_db()
        print("[Startup] Database tables initialized.")
    except Exception as e:  # noqa: BLE001
        print(
            f"[Startup Warning] Database connection warning ({e}). Running in degraded mode."
        )

    yield
    print("[Shutdown] Cleaning up services...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated Short-Form Viral Video Generation Platform Backend",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggregate domain routers under API v1 prefix
v1_router = APIRouter(prefix=settings.API_V1_STR)
v1_router.include_router(users_router)
v1_router.include_router(trends_router)
v1_router.include_router(scripts_router)
v1_router.include_router(videos_router)

app.include_router(v1_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
