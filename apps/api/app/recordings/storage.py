from typing import Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.config import Settings


class RecordingStorage(Protocol):
    """Private object storage contract implemented by S3 and MinIO."""

    def upload_url(self, key: str, content_type: str, expires_in: int) -> str: ...
    def download_url(self, key: str, expires_in: int) -> str: ...
    def delete(self, key: str) -> None: ...


class S3RecordingStorage:
    def __init__(self, settings: Settings, client: BaseClient | None = None) -> None:
        self._bucket = settings.recording_bucket
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.recording_s3_endpoint_url,
            region_name=settings.recording_s3_region,
            config=Config(signature_version="s3v4"),
        )

    def upload_url(self, key: str, content_type: str, expires_in: int) -> str:
        return str(self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        ))

    def download_url(self, key: str, expires_in: int) -> str:
        return str(self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        ))

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
