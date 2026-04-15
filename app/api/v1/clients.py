from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.client import ClientCreate, ClientListResponse, ClientRead, ClientStatusUpdate, ClientUpdate
from app.services.clients import client_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ClientListResponse:
    items, total = client_service.list(db, search=search, page=page, size=size)
    return ClientListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=ClientRead, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> ClientRead:
    return client_service.create(db, payload, user)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> ClientRead:
    return client_service.get(db, client_id)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ClientRead:
    return client_service.update(db, client_id, payload, user)


@router.patch("/{client_id}/status", response_model=ClientRead)
def update_client_status(
    client_id: str,
    payload: ClientStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ClientRead:
    return client_service.update(db, client_id, ClientUpdate(status=payload.status), user)

