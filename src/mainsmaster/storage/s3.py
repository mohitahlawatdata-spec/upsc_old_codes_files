"""S3-compatible artifact storage for Cloudflare R2, MinIO, or AWS S3."""

import mimetypes
from pathlib import Path

from mainsmaster.settings import Settings


class S3ArtifactStore:
    def __init__(self, settings: Settings):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use S3-compatible artifact storage") from exc
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        if settings.s3_create_bucket:
            self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001 - provider errors vary across S3 implementations
            self.client.create_bucket(Bucket=self.bucket)

    def upload_tree(self, source: Path, prefix: str) -> list[str]:
        prefix = prefix.strip("/")
        uploaded = []
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            key = f"{prefix}/{relative}"
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.client.upload_file(
                str(path),
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            uploaded.append(key)
        return uploaded

    def delete_prefix(self, prefix: str) -> None:
        prefix = prefix.strip("/") + "/"
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})
