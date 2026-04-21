from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import public_role_value, role_level
from app.core.rate_limit import login_rate_limit, password_reset_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth import auth_service
from app.services.redis import get_redis

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = auth_service.authenticate(db, payload.email, payload.password)
    return auth_service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return auth_service.refresh(db, payload.refresh_token)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    dependencies=[Depends(password_reset_rate_limit)],
)
async def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    return await auth_service.request_password_reset(db, redis, str(payload.email))


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    dependencies=[Depends(password_reset_rate_limit)],
)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    return await auth_service.confirm_password_reset(db, redis, payload.token, payload.password)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=public_role_value(user.role),
        role_level=role_level(user.role),
    )
