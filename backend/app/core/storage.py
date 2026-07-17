import hashlib
import uuid
from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()

_S3_BACKENDS = frozenset({"r2", "neon", "s3"})


def _local_root() -> Path:
    root = Path(settings.local_upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object_key(user_id: uuid.UUID, card_id: uuid.UUID, ext: str) -> str:
    """S3 object key; matches DB/public path without leading slash."""
    return f"uploads/{user_id}/{card_id}.{ext}"


def _public_ref(user_id: uuid.UUID, card_id: uuid.UUID, ext: str) -> str:
    return f"/uploads/{user_id}/{card_id}.{ext}"


async def save_image(user_id: uuid.UUID, card_id: uuid.UUID, data: bytes, ext: str = "jpg") -> str:
    """Save image and return canonical media ref for DB (/uploads/...)."""
    backend = (settings.storage_backend or "local").strip().lower()
    if backend in _S3_BACKENDS and _s3_configured(backend):
        return _save_s3(backend, user_id, card_id, data, ext)
    return _save_local(user_id, card_id, data, ext)


def _s3_configured(backend: str) -> bool:
    if backend == "r2":
        return bool(settings.r2_bucket_name and settings.r2_access_key_id and settings.r2_secret_access_key)
    return bool(
        settings.s3_endpoint_url
        and settings.s3_access_key_id
        and settings.s3_secret_access_key
        and settings.s3_bucket_name
    )


def _save_local(user_id: uuid.UUID, card_id: uuid.UUID, data: bytes, ext: str) -> str:
    user_dir = _local_root() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{card_id}.{ext}"
    path.write_bytes(data)
    return _public_ref(user_id, card_id, ext)


def _s3_client(backend: str):
    if backend == "r2":
        if not settings.r2_account_id:
            raise RuntimeError("R2_ACCOUNT_ID is required when STORAGE_BACKEND=r2")
        return boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    return boto3.client(
        "s3",
        region_name=settings.s3_region or "us-east-2",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _s3_bucket(backend: str) -> str:
    if backend == "r2":
        assert settings.r2_bucket_name
        return settings.r2_bucket_name
    assert settings.s3_bucket_name
    return settings.s3_bucket_name


def _save_s3(
    backend: str,
    user_id: uuid.UUID,
    card_id: uuid.UUID,
    data: bytes,
    ext: str,
) -> str:
    # R2 legacy keys omit the uploads/ prefix; Neon/generic S3 keep path aligned with public URL.
    if backend == "r2":
        key = f"{user_id}/{card_id}.{ext}"
    else:
        key = _object_key(user_id, card_id, ext)

    client = _s3_client(backend)
    client.put_object(
        Bucket=_s3_bucket(backend),
        Key=key,
        Body=data,
        ContentType=f"image/{ext}",
    )
    return _public_ref(user_id, card_id, ext)
