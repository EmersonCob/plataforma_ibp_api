import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from app.core.security import decode_token, generate_public_token, hash_password, verify_password, create_access_token  # noqa: E402


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("ChangeMe123!")
    assert password_hash != "ChangeMe123!"
    assert verify_password("ChangeMe123!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_public_token_is_random_and_url_safe() -> None:
    token_a = generate_public_token()
    token_b = generate_public_token()
    assert token_a != token_b
    assert len(token_a) >= 48
    assert "/" not in token_a


def test_jwt_contains_subject_and_role() -> None:
    token = create_access_token("user-id", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-id"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"

