from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserDirectoryEntry, UserListResponse, UserProfileUpdate, UserRead, UserStatusUpdate, UserUpdate
from app.services.users import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
def list_users(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserListResponse:
    items, total = user_service.list(db, search=search, page=page, size=size)
    return UserListResponse(items=items, total=total, page=page, size=size)


@router.get("/directory", response_model=list[UserDirectoryEntry])
def list_user_directory(
    search: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> list[UserDirectoryEntry]:
    return user_service.directory(db, search=search, limit=limit)


@router.get("/me", response_model=UserRead)
def get_my_profile(actor: User = Depends(require_user)) -> UserRead:
    return actor


@router.put("/me", response_model=UserRead)
def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_user),
) -> UserRead:
    return user_service.update_profile(db, actor=actor, payload=payload)


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_admin)) -> UserRead:
    return user_service.create(db, payload, actor)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> UserRead:
    return user_service.get(db, user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> UserRead:
    return user_service.update(db, user_id, payload, actor)


@router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> UserRead:
    return user_service.update_status(db, user_id, payload.is_active, actor)
