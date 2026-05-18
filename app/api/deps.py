from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import role_level
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if role_level(user.role) < 5:
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    if role_level(user.role) < 2:
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return user


def require_user(user: User = Depends(get_current_user)) -> User:
    if role_level(user.role) < 1:
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return user


def require_min_role(min_level: int) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if role_level(user.role) < min_level:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return user

    return dependency
