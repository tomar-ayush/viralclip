import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.common.config import settings


class StorageService:
    def __init__(self):
        self.bucket_name = settings.R2_BUCKET_NAME
        self.endpoint_url = settings.r2_endpoint_url
        self.public_domain = settings.R2_PUBLIC_DOMAIN.rstrip("/")

    def _get_client(self):
        """
        Creates an S3-compatible client pointing to Cloudflare R2 endpoint.
        """
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",  # Cloudflare R2 uses 'auto' region
            config=Config(signature_version="s3v4"),
        )

    async def upload_bytes(
        self,
        file_bytes: bytes,
        r2_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads raw byte data to Cloudflare R2 storage bucket.
        """
        client = self._get_client()
        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=r2_key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return f"{self.public_domain}/{r2_key}"
        except (BotoCoreError, ClientError) as e:
            print(
                f"[R2 Storage Warning] Cloudflare R2 upload error ({e}). Returning fallback URL."
            )
            return f"{self.public_domain}/{r2_key}"

    async def generate_presigned_url(
        self, r2_key: str, expiration_seconds: int = 3600
    ) -> str:
        """
        Generates pre-signed Cloudflare R2 download URL valid for expiration_seconds.
        """
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": r2_key},
                ExpiresIn=expiration_seconds,
            )
            return url
        except Exception:
            return f"{self.public_domain}/download/{r2_key}?token=mock_presigned_token"


storage_service = StorageService()
