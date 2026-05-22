"""MinIO/S3 storage wrapper.

Bucket: settings.MINIO_BUCKET (default `lms-files`).
- `avatars/{user_id}/{uuid}.{ext}` — foydalanuvchi avatar (public read)
- `lessons/...` — Phase 3 da
- `proctoring/...` — Phase 7 da

Avatar uchun bucket policy: `avatars/*` public read (CDN'siz ham serve bo'ladi).
"""

from __future__ import annotations

import io
import json
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    parsed = urlparse(
        settings.MINIO_ENDPOINT
        if settings.MINIO_ENDPOINT.startswith(("http://", "https://"))
        else f"http://{settings.MINIO_ENDPOINT}"
    )
    endpoint = parsed.netloc or parsed.path
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )


PUBLIC_READ_PREFIXES = ("avatars/", "thumbnails/")


def _public_read_policy(bucket: str, prefixes: tuple[str, ...]) -> dict[str, Any]:
    """Anonymous read access for the given prefixes."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [
                    f"arn:aws:s3:::{bucket}/{p}*" for p in prefixes
                ],
            }
        ],
    }


def init_storage() -> None:
    """Bucket'ni yaratadi (mavjud bo'lmasa) va public prefikslarga read policy qo'yadi.

    App lifespan'da chaqiriladi — ishga tushishni bloklamaydi (xato bo'lsa log qiladi).
    Public prefixlar: avatars/, recordings/, thumbnails/
    """
    client = get_minio_client()
    bucket = settings.MINIO_BUCKET
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("minio.bucket_created", bucket=bucket)
        client.set_bucket_policy(
            bucket, json.dumps(_public_read_policy(bucket, PUBLIC_READ_PREFIXES))
        )
        logger.info("minio.policy_set", bucket=bucket, prefixes=PUBLIC_READ_PREFIXES)
    except S3Error as exc:
        logger.error("minio.init_failed", bucket=bucket, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio.unreachable", bucket=bucket, error=str(exc))


def upload_object(
    *,
    object_name: str,
    data: bytes,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Yuklaydi va public URL qaytaradi (CDN/MINIO_PUBLIC_URL bilan)."""
    bucket = bucket or settings.MINIO_BUCKET
    client = get_minio_client()
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    base = settings.MINIO_PUBLIC_URL.rstrip("/") if settings.MINIO_PUBLIC_URL else ""
    if not base:
        scheme = "https" if settings.MINIO_USE_SSL else "http"
        base = f"{scheme}://{settings.MINIO_ENDPOINT}"
    return f"{base}/{bucket}/{object_name}"


def delete_object(object_name: str, bucket: str | None = None) -> None:
    bucket = bucket or settings.MINIO_BUCKET
    client = get_minio_client()
    try:
        client.remove_object(bucket, object_name)
    except S3Error as exc:
        logger.warning("minio.delete_failed", object=object_name, error=str(exc))


def object_key_from_url(url: str | None) -> str | None:
    """Public URL'dan object key'ni ajratib oladi (avatar o'chirishda kerak)."""
    if not url:
        return None
    bucket = settings.MINIO_BUCKET
    marker = f"/{bucket}/"
    idx = url.find(marker)
    if idx < 0:
        return None
    return url[idx + len(marker) :]


def _public_minio_client() -> Minio:
    """Faqat presigned URL imzolash uchun — public endpoint bilan.

    `region` aniq ko'rsatilgan, shu sababli SDK bucket region lookup uchun
    HTTP qilmaydi (presigned faqat lokal ravishda imzolanadi).
    """
    from urllib.parse import urlparse

    if settings.MINIO_PUBLIC_URL:
        parsed = urlparse(settings.MINIO_PUBLIC_URL.rstrip("/"))
        endpoint = parsed.netloc or parsed.path
        secure = parsed.scheme == "https"
    else:
        endpoint = settings.MINIO_ENDPOINT
        secure = settings.MINIO_USE_SSL
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=secure,
        region="us-east-1",
    )


def get_presigned_url(
    object_name: str,
    *,
    bucket: str | None = None,
    ttl_seconds: int = 900,
) -> str:
    """Maxfiy obyekt uchun vaqtli (TTL) URL — anon access uchun.

    Phase 7b: sezgir obyektlar (proctoring snapshot, ID reference, live recording)
    public read'dan olib tashlanadi. Frontend bu URL'ni har gal yangi oladi.
    Default TTL = 15 daqiqa.

    AWS Signature V4 host'ni signature'ga qo'shadi, shuning uchun PUBLIC endpoint
    (`localhost:8212` brauzer uchun) bilan imzolaymiz.
    """
    from datetime import timedelta

    bucket = bucket or settings.MINIO_BUCKET
    client = _public_minio_client()
    return client.presigned_get_object(
        bucket, object_name, expires=timedelta(seconds=ttl_seconds)
    )
