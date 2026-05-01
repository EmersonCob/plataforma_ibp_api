from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.prontuario import ProntuarioCreate, ProntuarioListResponse, ProntuarioRead, ProntuarioUpdate
from app.services.prontuario import prontuario_service

router = APIRouter(prefix="/prontuario", tags=["Prontuário"])


@router.get("", response_model=ProntuarioListResponse)
def list_prontuario_entries(
    client_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProntuarioListResponse:
    items, total = prontuario_service.list(db, client_id=client_id, search=search, page=page, size=size)
    return ProntuarioListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=ProntuarioRead, status_code=status.HTTP_201_CREATED)
def create_prontuario_entry(
    payload: ProntuarioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProntuarioRead:
    return prontuario_service.create(db, payload, user)


@router.get("/{entry_id}", response_model=ProntuarioRead)
def get_prontuario_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProntuarioRead:
    return prontuario_service.get(db, entry_id)


@router.put("/{entry_id}", response_model=ProntuarioRead)
def update_prontuario_entry(
    entry_id: str,
    payload: ProntuarioUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProntuarioRead:
    return prontuario_service.update(db, entry_id, payload, user)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prontuario_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    prontuario_service.delete(db, entry_id, user)
