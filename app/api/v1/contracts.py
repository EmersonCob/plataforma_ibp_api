from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_manager, require_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.contract import ContractTemplate
from app.models.enums import ContractStatus, NotificationChannel
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractListResponse,
    ContractRead,
    ContractTemplateRead,
    ContractUpdate,
    ContractVersionCreate,
    ContractVersionRead,
    GenerateLinkRequest,
    SignedDocumentResponse,
    SignLinkResponse,
)
from app.services.contracts import contract_service
from app.services.notifications import notification_gateway
from app.services.storage import storage_service

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("/templates", response_model=list[ContractTemplateRead])
def list_templates(db: Session = Depends(get_db), _: User = Depends(require_user)) -> list[ContractTemplate]:
    return list(db.scalars(select(ContractTemplate).where(ContractTemplate.is_active.is_(True)).order_by(ContractTemplate.name)).all())


@router.get("", response_model=ContractListResponse)
def list_contracts(
    search: str | None = None,
    status: ContractStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ContractListResponse:
    items, total = contract_service.list(db, search=search, status=status, page=page, size=size)
    return ContractListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=ContractRead, status_code=201)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user: User = Depends(require_user)) -> ContractRead:
    return contract_service.create(db, payload, user)


@router.get("/{contract_id}", response_model=ContractRead)
def get_contract(contract_id: str, db: Session = Depends(get_db), _: User = Depends(require_user)) -> ContractRead:
    return contract_service.get(db, contract_id)


@router.put("/{contract_id}", response_model=ContractRead)
def update_contract(
    contract_id: str,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> ContractRead:
    return contract_service.update(db, contract_id, payload, user)


@router.post("/{contract_id}/generate-link", response_model=SignLinkResponse)
async def generate_link(
    contract_id: str,
    payload: GenerateLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> SignLinkResponse:
    contract, sign_url = contract_service.generate_link(db, contract_id, user, payload.expires_at)
    if payload.trigger_notification:
        await notification_gateway.trigger_contract_event(
            db,
            contract=contract,
            event_type="contract_link_generated",
            channel=NotificationChannel.whatsapp,
        )
    return SignLinkResponse(token=contract.generated_link_token or "", sign_url=sign_url, expires_at=contract.link_expires_at)


@router.post("/{contract_id}/cancel", response_model=ContractRead)
def cancel_contract(contract_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)) -> ContractRead:
    return contract_service.cancel(db, contract_id, user)


@router.post("/{contract_id}/expire", response_model=ContractRead)
def expire_contract(contract_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)) -> ContractRead:
    return contract_service.expire(db, contract_id, user)


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: str, db: Session = Depends(get_db), user: User = Depends(require_manager)) -> None:
    contract_service.delete(db, contract_id, user)


@router.get("/{contract_id}/versions", response_model=list[ContractVersionRead])
def list_versions(contract_id: str, db: Session = Depends(get_db), _: User = Depends(require_user)) -> list:
    return contract_service.versions(db, contract_id)


@router.post("/{contract_id}/versions", response_model=ContractVersionRead, status_code=201)
def create_version(
    contract_id: str,
    payload: ContractVersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return contract_service.add_version(db, contract_id, payload.content, user)


@router.get("/{contract_id}/signed-document", response_model=SignedDocumentResponse)
def get_signed_document(
    contract_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> dict:
    contract = contract_service.get(db, contract_id)
    return contract_service.signed_document_response(contract)


@router.post("/{contract_id}/generate-signed-document", response_model=SignedDocumentResponse)
def generate_signed_document(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> dict:
    contract = contract_service.generate_signed_document(db, contract_id, user)
    return contract_service.signed_document_response(contract)


@router.get("/{contract_id}/audit")
def get_contract_audit(contract_id: str, db: Session = Depends(get_db), _: User = Depends(require_user)) -> list[dict]:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "contract", AuditLog.entity_id == contract_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": row.id,
            "action": row.action,
            "actor_type": row.actor_type.value,
            "actor_id": row.actor_id,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/{contract_id}/signature-evidence")
def get_signature_evidence(contract_id: str, db: Session = Depends(get_db), _: User = Depends(require_user)) -> dict:
    contract = contract_service.get(db, contract_id)
    if not contract.signature:
        return {"face_photo_url": None, "signature_image_url": None}
    return {
        "face_photo_url": storage_service.presigned_get_url(contract.signature.face_photo_path),
        "signature_image_url": storage_service.presigned_get_url(contract.signature.signature_image_path),
        "signer_name": contract.signature.signer_name,
        "signed_at": contract.signature.signed_at,
        "ip_address": contract.signature.ip_address,
        "user_agent": contract.signature.user_agent,
    }
