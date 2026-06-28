"""Tests for `src.core.security` — password hashing + JWT helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from src.core.config import settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("right")
    assert verify_password("wrong", hashed) is False


def test_verify_password_on_garbage_hash_returns_false() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_create_and_decode_access_token_roundtrip() -> None:
    account_id = uuid.uuid4()
    permissions = ["write_lead", "read_leads"]

    token = create_access_token(account_id, role="attorney", permissions=permissions)
    claims = decode_access_token(token)

    assert claims["sub"] == str(account_id)
    assert claims["role"] == "attorney"
    assert claims["permissions"] == sorted(permissions)
    assert "exp" in claims


def test_create_access_token_sorts_permissions_deterministically() -> None:
    account_id = uuid.uuid4()
    a = create_access_token(account_id, role="admin", permissions=["b", "a", "c"])
    b = create_access_token(account_id, role="admin", permissions=["c", "a", "b"])
    assert decode_access_token(a)["permissions"] == decode_access_token(b)["permissions"]


def test_expired_token_raises_jwt_error() -> None:
    payload = {
        "sub": str(uuid.uuid4()),
        "role": "admin",
        "permissions": [],
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(JWTError):
        decode_access_token(expired)


def test_tampered_token_raises_jwt_error() -> None:
    token = create_access_token(uuid.uuid4(), role="admin", permissions=[])
    tampered = token + "abc"
    with pytest.raises(JWTError):
        decode_access_token(tampered)


def test_wrong_secret_raises_jwt_error() -> None:
    payload = {
        "sub": str(uuid.uuid4()),
        "role": "admin",
        "permissions": [],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    foreign = jwt.encode(payload, "different-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(JWTError):
        decode_access_token(foreign)


def test_explicit_expires_minutes_overrides_default() -> None:
    account_id = uuid.uuid4()
    token = create_access_token(account_id, role="admin", permissions=[], expires_minutes=1)
    claims = decode_access_token(token)
    exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    delta = exp - datetime.now(timezone.utc)
    assert delta < timedelta(minutes=2)
