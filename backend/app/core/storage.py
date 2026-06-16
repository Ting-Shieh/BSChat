import hashlib
import uuid
from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


def _local_root() -> Path:
    root = Path(settings.local_upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def save_image(user_id: uuid.UUID, card_id: uuid.UUID, data: bytes, ext: str = "jpg") -> str:
    """Save image and return public URL."""
    if settings.storage_backend == "r2" and settings.r2_bucket_name:
        return _save_r2(user_id, card_id, data, ext)
    return _save_local(user_id, card_id, data, ext)


def _save_local(user_id: uuid.UUID, card_id: uuid.UUID, data: bytes, ext: str) -> str:
    user_dir = _local_root() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{card_id}.{ext}"
    path.write_bytes(data)
    return f"/uploads/{user_id}/{card_id}.{ext}"


def _save_r2(user_id: uuid.UUID, card_id: uuid.UUID, data: bytes, ext: str) -> str:
    key = f"{user_id}/{card_id}.{ext}"
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    )
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=data,
        ContentType=f"image/{ext}",
    )
    return f"/uploads/{user_id}/{card_id}.{ext}"
