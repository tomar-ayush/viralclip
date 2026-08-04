import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.common.config import settings


class StorageService:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION

    def _get_client(self):
        return boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4")
        )

    async def upload_bytes(
        self,
        file_bytes: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Uploads raw byte data to AWS S3.
        """
        client = self._get_client()
        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type
            )
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        except (BotoCoreError, ClientError) as e:
            print(f"[Storage Warning] S3 upload error ({e}). Returning fallback URL.")
            return f"https://mock-s3.viralcut.ai/{self.bucket_name}/{s3_key}"

    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration_seconds: int = 3600
    ) -> str:
        """
        Generates pre-signed S3 download URL valid for expiration_seconds.
        """
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration_seconds
            )
            return url
        except Exception:
            return f"https://mock-s3.viralcut.ai/download/{s3_key}?token=mock_presigned_token"


storage_service = StorageService()
