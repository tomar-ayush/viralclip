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

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Settings (32-byte key for AES-256-GCM and JWT)
    ENCRYPTION_MASTER_KEY: str = "4f8a9b2c1d3e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a"
    JWT_SECRET_KEY: str = "super_secret_jwt_key_9a8b7c6d5e4f3a2b1c0d"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Cloudflare R2 Storage (S3 Compatible API)
    CLOUDFLARE_ACCOUNT_ID: str = "mock-cloudflare-account-id"
    R2_ACCESS_KEY_ID: str = "mock-r2-access-key-id"
    R2_SECRET_ACCESS_KEY: str = "mock-r2-secret-access-key"
    R2_BUCKET_NAME: str = "viral-video-assets-bucket"
    R2_PUBLIC_DOMAIN: str = "https://pub-r2.viralcut.ai"

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # AWS Remotion Lambda Config
    REMOTION_LAMBDA_FUNCTION_NAME: str = "remotion-render-function"
    REMOTION_SERVE_URL: str = "https://pub-r2.viralcut.ai/sites/viral-short-template/index.html"
    REMOTION_COMPOSITION_ID: str = "ShortVideoComposition"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
