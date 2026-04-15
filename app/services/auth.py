from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User


class AuthService:
    def authenticate(self, db: Session, email: str, password: str) -> User:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if not user or not verify_password(password, user.password_hash):
            raise AppError("E-mail ou senha inválidos", 401, "invalid_credentials")
        if not user.is_active:
            raise AppError("Usuário inativo", 403, "inactive_user")
        return user

    def issue_tokens(self, user: User) -> dict[str, str]:
        return {
            "access_token": create_access_token(user.id, user.role.value),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
        }

    def refresh(self, db: Session, refresh_token: str) -> dict[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = db.get(User, payload["sub"])
        if not user or not user.is_active:
            raise AppError("Token inválido", 401, "invalid_token")
        return self.issue_tokens(user)


auth_service = AuthService()

