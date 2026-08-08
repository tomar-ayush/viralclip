from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ViralCut AI Backend"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "viral_video_db"
    DATABASE_URL: str | None = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Settings (Upstash \u2014 uses rediss:// with TLS + password)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""      # set for Upstash; empty = no auth (local dev)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Settings (32-byte key for AES-256-GCM and JWT)
    ENCRYPTION_MASTER_KEY: str = "4f8a9b2c1d3e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a"
    JWT_SECRET_KEY: str = "super_secret_jwt_key_9a8b7c6d5e4f3a2b1c0d"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # IDrive E2 Storage (S3 Compatible)
    E2_ENDPOINT_URL: str = "https://s3.ap-northeast-1.idrivee2.com"
    E2_REGION: str = "ap-northeast-1"
    E2_ACCESS_KEY_ID: str = "HSgQGGT8aN3SeBVnKUuq"
    E2_SECRET_ACCESS_KEY: str = "eJER6sWyS0hwSZRyTpoo6qDLF4v6IU7QHfANNhKc"
    E2_BUCKET_NAME: str = "viralclip"
    E2_PUBLIC_DOMAIN: str = "https://s3.ap-northeast-1.idrivee2.com/viralclip"

    # FFmpeg Render Microservice (deploy render_service/ to HuggingFace/Render/Koyeb)
    RENDER_SERVICE_URL: str = "http://localhost:7860"  # override with deployed URL
    RENDER_SECRET: str = "changeme"                    # shared secret for auth

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
