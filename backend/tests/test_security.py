import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_token_roundtrip():
    user_id = uuid.uuid4()
    assert decode_access_token(create_access_token(user_id)) == user_id


def test_tampered_token_is_rejected():
    token = create_access_token(uuid.uuid4())
    assert decode_access_token(token[:-2] + "xx") is None


def test_token_signed_with_other_secret_is_rejected():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(hours=1)},
        "some-other-secret",
        algorithm=ALGORITHM,
    )
    assert decode_access_token(token) is None


def test_expired_token_is_rejected():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        get_settings().jwt_secret,
        algorithm=ALGORITHM,
    )
    assert decode_access_token(token) is None


def test_garbage_is_rejected():
    assert decode_access_token("not-a-token") is None
