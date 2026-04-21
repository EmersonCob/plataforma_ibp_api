import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from app.services.auth import auth_service  # noqa: E402


def test_password_reset_key_does_not_store_raw_token() -> None:
    token = "token-publico-muito-seguro-com-tamanho-suficiente"
    key = auth_service._password_reset_key(token)

    assert key.startswith("password-reset:")
    assert token not in key
    assert len(key) == len("password-reset:") + 64

