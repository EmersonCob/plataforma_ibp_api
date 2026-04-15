import base64
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: UUID | str, role: str, expires_delta: timedelta | None = None) -> str:
    expires = now_utc() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "exp": expires,
        "iat": now_utc(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: UUID | str, expires_delta: timedelta | None = None) -> str:
    expires = now_utc() + (expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "exp": expires,
        "iat": now_utc(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token inválido") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Tipo de token inválido")
    return payload


def generate_public_token() -> str:
    return secrets.token_urlsafe(48)


def decode_data_url(data_url: str, expected_prefix: str = "data:image/png;base64,") -> bytes:
    if not data_url.startswith(expected_prefix):
        raise ValueError("Formato de assinatura inválido")
    raw = data_url[len(expected_prefix) :]
    try:
        return base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Assinatura inválida") from exc

