import hashlib
import secrets
from urllib.parse import urlencode

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.permissions import public_role_value
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.enums import ActorType
from app.models.user import User
from app.services.audit import audit_service
from app.services.email import email_service


PASSWORD_RESET_GENERIC_MESSAGE = "Se o e-mail estiver cadastrado e ativo, enviaremos as instruções de recuperação."


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
            "access_token": create_access_token(user.id, public_role_value(user.role)),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
        }

    def refresh(self, db: Session, refresh_token: str) -> dict[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = db.get(User, payload["sub"])
        if not user or not user.is_active:
            raise AppError("Token inválido", 401, "invalid_token")
        return self.issue_tokens(user)

    async def request_password_reset(self, db: Session, redis: Redis, email: str) -> dict[str, str]:
        normalized_email = email.lower()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if not user or not user.is_active:
            return {"message": PASSWORD_RESET_GENERIC_MESSAGE}

        token = secrets.token_urlsafe(48)
        expires_seconds = settings.password_reset_token_expire_minutes * 60
        await redis.setex(self._password_reset_key(token), expires_seconds, user.id)

        reset_url = self._build_password_reset_url(token)
        email_service.send_password_reset_email(user, reset_url, settings.password_reset_token_expire_minutes)
        audit_service.log(
            db,
            entity_type="user",
            entity_id=user.id,
            action="password_reset_requested",
            actor_type=ActorType.system,
            metadata={"email": user.email},
        )
        db.commit()
        return {"message": PASSWORD_RESET_GENERIC_MESSAGE}

    async def confirm_password_reset(self, db: Session, redis: Redis, token: str, password: str) -> dict[str, str]:
        key = self._password_reset_key(token)
        user_id = await redis.get(key)
        if not user_id:
            raise AppError("Link de redefinição inválido ou expirado.", 410, "password_reset_token_invalid")

        user = db.get(User, user_id)
        if not user or not user.is_active:
            await redis.delete(key)
            raise AppError("Link de redefinição inválido ou expirado.", 410, "password_reset_token_invalid")

        user.password_hash = hash_password(password)
        audit_service.log(
            db,
            entity_type="user",
            entity_id=user.id,
            action="password_reset_completed",
            actor_type=ActorType.system,
            metadata={"email": user.email},
        )
        db.commit()
        await redis.delete(key)
        return {"message": "Senha redefinida com sucesso. Você já pode entrar com a nova senha."}

    def _build_password_reset_url(self, token: str) -> str:
        query = urlencode({"token": token})
        return f"{settings.frontend_app_url.rstrip('/')}/login/redefinir-senha?{query}"

    def _password_reset_key(self, token: str) -> str:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"password-reset:{token_hash}"


auth_service = AuthService()
