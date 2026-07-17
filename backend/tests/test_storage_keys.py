"""Storage key helpers for Neon / S3 uploads."""

import uuid

from app.core.storage import _object_key, _public_ref


def test_object_key_aligns_with_public_ref():
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    card_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    assert _object_key(user_id, card_id, "jpg") == f"uploads/{user_id}/{card_id}.jpg"
    assert _public_ref(user_id, card_id, "jpg") == f"/uploads/{user_id}/{card_id}.jpg"
