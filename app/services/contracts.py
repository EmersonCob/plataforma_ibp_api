from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import AppError, not_found
from app.core.security import generate_public_token, now_utc
from app.models.client import Client
from app.models.contract import Contract, ContractVersion
from app.models.enums import ActorType, ContractStatus
from app.models.user import User
from app.repositories.contracts import contract_repository
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services.audit import audit_service
from app.services.document import document_service
from app.services.storage import storage_service

LOCKED_STATUSES = {ContractStatus.assinado, ContractStatus.cancelado, ContractStatus.expirado}


class ContractService:
    def list(
        self,
        db: Session,
        *,
        search: str | None,
        status: ContractStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[Contract], int]:
        return contract_repository.list(db, search=search, status=status, page=page, size=size)

    def get(self, db: Session, contract_id: str) -> Contract:
        contract = db.scalar(
            select(Contract)
            .options(joinedload(Contract.client), joinedload(Contract.signature))
            .where(Contract.id == contract_id)
        )
        if not contract:
            raise not_found("Contrato não encontrado")
        return contract

    def create(self, db: Session, payload: ContractCreate, user: User) -> Contract:
        client = db.get(Client, payload.client_id)
        if not client:
            raise not_found("Cliente não encontrado")

        contract = Contract(
            client_id=payload.client_id,
            template_id=payload.template_id,
            title=payload.title,
            content=payload.content,
            created_by=user.id,
            status=ContractStatus.rascunho,
            current_version=1,
        )
        db.add(contract)
        db.flush()
        db.add(
            ContractVersion(
                contract_id=contract.id,
                version_number=1,
                content=payload.content,
                changed_by=user.id,
                created_at=now_utc(),
                metadata_json={"reason": "initial_version"},
            )
        )
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_created",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.commit()
        return self.get(db, contract.id)

    def update(self, db: Session, contract_id: str, payload: ContractUpdate, user: User) -> Contract:
        contract = self.get(db, contract_id)
        if contract.status == ContractStatus.assinado:
            raise AppError("Contrato assinado não pode ser editado. Crie uma nova versão/contrato.", 409, "signed_contract_locked")
        if contract.status in {ContractStatus.cancelado, ContractStatus.expirado}:
            raise AppError("Contrato cancelado ou expirado não pode ser editado.", 409, "contract_locked")

        updates = payload.model_dump(exclude_unset=True)
        content_changed = "content" in updates and updates["content"] != contract.content

        if "title" in updates:
            contract.title = updates["title"]
        if content_changed:
            contract.content = updates["content"]
            contract.current_version += 1
            contract.status = ContractStatus.em_edicao
            db.add(
                ContractVersion(
                    contract_id=contract.id,
                    version_number=contract.current_version,
                    content=contract.content,
                    changed_by=user.id,
                    created_at=now_utc(),
                    metadata_json={"reason": "admin_edit"},
                )
            )
        if "status" in updates and updates["status"] not in LOCKED_STATUSES:
            contract.status = updates["status"]

        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_updated",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"fields": list(updates.keys()), "new_version": contract.current_version if content_changed else None},
        )
        db.commit()
        return self.get(db, contract.id)

    def generate_link(self, db: Session, contract_id: str, user: User, expires_at: datetime | None = None) -> tuple[Contract, str]:
        contract = self.get(db, contract_id)
        if contract.status in LOCKED_STATUSES:
            raise AppError("Não é possível gerar link para contrato bloqueado.", 409, "contract_locked")

        contract.generated_link_token = generate_public_token()
        contract.link_expires_at = expires_at
        contract.status = ContractStatus.aguardando_assinatura
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_link_generated",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"expires_at": expires_at.isoformat() if expires_at else None},
        )
        db.commit()
        db.refresh(contract)
        sign_url = f"{settings.public_sign_url_base.rstrip('/')}/{contract.generated_link_token}"
        return contract, sign_url

    def cancel(self, db: Session, contract_id: str, user: User) -> Contract:
        contract = self.get(db, contract_id)
        if contract.status == ContractStatus.assinado:
            raise AppError("Contrato assinado não pode ser cancelado.", 409, "signed_contract_locked")
        contract.status = ContractStatus.cancelado
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_cancelled",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.commit()
        return self.get(db, contract.id)

    def expire(self, db: Session, contract_id: str, user: User) -> Contract:
        contract = self.get(db, contract_id)
        if contract.status == ContractStatus.assinado:
            raise AppError("Contrato assinado não pode ser expirado.", 409, "signed_contract_locked")
        contract.status = ContractStatus.expirado
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_expired",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.commit()
        return self.get(db, contract.id)

    def delete(self, db: Session, contract_id: str, user: User) -> None:
        contract = self.get(db, contract_id)
        if contract.status == ContractStatus.assinado or contract.signature:
            raise AppError("Contrato assinado não pode ser apagado.", 409, "signed_contract_locked")

        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_deleted",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"title": contract.title, "status": contract.status.value},
        )
        db.delete(contract)
        db.commit()

    def versions(self, db: Session, contract_id: str) -> list[ContractVersion]:
        self.get(db, contract_id)
        return list(
            db.scalars(
                select(ContractVersion)
                .where(ContractVersion.contract_id == contract_id)
                .order_by(ContractVersion.version_number.desc())
            ).all()
        )

    def add_version(self, db: Session, contract_id: str, content: str, user: User) -> ContractVersion:
        contract = self.get(db, contract_id)
        if contract.status == ContractStatus.assinado:
            raise AppError("Contrato assinado é imutável.", 409, "signed_contract_locked")

        contract.current_version += 1
        contract.content = content
        contract.status = ContractStatus.em_edicao
        version = ContractVersion(
            contract_id=contract.id,
            version_number=contract.current_version,
            content=content,
            changed_by=user.id,
            created_at=now_utc(),
            metadata_json={"reason": "manual_version"},
        )
        db.add(version)
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="contract_version_created",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"version": contract.current_version},
        )
        db.commit()
        db.refresh(version)
        return version

    def generate_signed_document(self, db: Session, contract_id: str, user: User | None = None) -> Contract:
        contract = self.get(db, contract_id)
        if contract.status != ContractStatus.assinado:
            raise AppError("Apenas contratos assinados podem gerar documento final.", 409, "contract_not_signed")
        document_service.generate_signed_pdf(db, contract)
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="signed_document_generated",
            actor_type=ActorType.admin if user else ActorType.system,
            actor_id=user.id if user else None,
        )
        db.commit()
        return self.get(db, contract.id)

    def signed_document_response(self, contract: Contract) -> dict:
        if not contract.signed_document_path:
            raise AppError("Documento final ainda não foi gerado.", 404, "signed_document_not_found")
        return {
            "contract_id": contract.id,
            "signed_document_path": contract.signed_document_path,
            "signed_document_url": storage_service.presigned_get_url(contract.signed_document_path),
            "signed_document_hash": contract.signed_document_hash,
            "generated_at": (contract.final_metadata or {}).get("generated_at"),
        }


contract_service = ContractService()
