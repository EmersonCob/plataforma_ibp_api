from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_user
from app.db.session import get_db
from app.models.enums import ClientStatus
from app.models.user import User
from app.schemas.client import ClientCreate, ClientListResponse, ClientRead, ClientStatusUpdate, ClientUpdate
from app.services.clients import client_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(
    search: str | None = None,
    status_filter: ClientStatus | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ClientListResponse:
    items, total = client_service.list(db, search=search, status=status_filter, page=page, size=size)
    return ClientListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=ClientRead, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user: User = Depends(require_user)) -> ClientRead:
    return client_service.create(db, payload, user)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: str, db: Session = Depends(get_db), _: User = Depends(require_user)) -> ClientRead:
    return client_service.get(db, client_id)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ClientRead:
    return client_service.update(db, client_id, payload, user)


@router.patch("/{client_id}/status", response_model=ClientRead)
def update_client_status(
    client_id: str,
    payload: ClientStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ClientRead:
    return client_service.update(db, client_id, ClientUpdate(status=payload.status), user)


@router.post("/{client_id}/photo", response_model=ClientRead)
async def upload_client_photo(
    client_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ClientRead:
    return await client_service.upload_photo(db, client_id, file, user)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    client_service.delete(db, client_id, user)
