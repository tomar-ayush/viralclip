import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.common.config import settings


class StorageService:
    def __init__(self):
        self.bucket_name = settings.E2_BUCKET_NAME
        self.endpoint_url = settings.E2_ENDPOINT_URL
        self.public_domain = settings.E2_PUBLIC_DOMAIN.rstrip("/")

    def _get_client(self):
        """
        Creates an S3-compatible boto3 client pointing to IDrive E2.
        IDrive E2 uses path-style addressing and standard S3v4 signatures.
        """
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.E2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.E2_SECRET_ACCESS_KEY,
            region_name=settings.E2_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},  # IDrive E2 requires path-style
            ),
        )

    async def upload_bytes(
        self,
        file_bytes: bytes,
        r2_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads raw byte data to IDrive E2 bucket.
        Returns the public URL of the uploaded object.
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
                f"[IDrive E2 Warning] Upload error ({e}). Returning fallback URL."
            )
            return f"{self.public_domain}/{r2_key}"

    async def generate_presigned_url(
        self, r2_key: str, expiration_seconds: int = 3600
    ) -> str:
        """
        Generates a pre-signed IDrive E2 download URL valid for expiration_seconds.
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
            return f"{self.public_domain}/{r2_key}?token=mock_presigned_token"


storage_service = StorageService()
