"""Where original files live: a local folder (laptop, tests) or S3 (production)."""

from functools import lru_cache
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import boto3

from app.config import get_settings

PRESIGNED_URL_SECONDS = 300


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def presigned_url(self, key: str, filename: str) -> str | None: ...


def inline_disposition(filename: str) -> str:
    # RFC 5987 encoding, so any filename (spaces, non-ASCII) is safe in the header
    return f"inline; filename*=UTF-8''{quote(filename)}"


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Key escapes the storage folder: {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def presigned_url(self, key: str, filename: str) -> str | None:
        return None  # the API streams local files itself


class S3Storage:
    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    def read(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def presigned_url(self, key: str, filename: str) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": inline_disposition(filename),
            },
            ExpiresIn=PRESIGNED_URL_SECONDS,
        )


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        if not settings.aws_s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 needs AWS_S3_BUCKET")
        return S3Storage(settings.aws_s3_bucket, settings.aws_region)
    return LocalStorage(Path(settings.local_storage_dir))
