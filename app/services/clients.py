from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.models.client import Client
from app.models.contract import Contract
from app.models.enums import ActorType, ClientStatus
from app.models.user import User
from app.repositories.clients import client_repository
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.audit import audit_service
from app.services.contract_rendering import build_client_contract_address
from app.services.storage import storage_service


class ClientService:
    def list(
        self,
        db: Session,
        *,
        search: str | None,
        status: ClientStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[Client], int]:
        items, total = client_repository.list(db, search=search, status=status, page=page, size=size)
        for item in items:
            self._attach_photo_url(item)
        return items, total

    def get(self, db: Session, client_id: str) -> Client:
        client = db.get(Client, client_id)
        if not client:
            raise not_found("Cliente não encontrado")
        self._attach_photo_url(client)
        return client

    def create(self, db: Session, payload: ClientCreate, user: User) -> Client:
        data = payload.model_dump()
        client = Client(**data)
        client.address = build_client_contract_address(client)
        db.add(client)
        db.flush()
        audit_service.log(
            db,
            entity_type="client",
            entity_id=client.id,
            action="client_created",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.commit()
        db.refresh(client)
        self._attach_photo_url(client)
        return client

    def update(self, db: Session, client_id: str, payload: ClientUpdate, user: User) -> Client:
        client = self.get(db, client_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(client, field, value)
        client.address = build_client_contract_address(client)
        audit_service.log(
            db,
            entity_type="client",
            entity_id=client.id,
            action="client_updated",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"fields": list(updates.keys())},
        )
        db.commit()
        db.refresh(client)
        self._attach_photo_url(client)
        return client

    async def upload_photo(self, db: Session, client_id: str, file: UploadFile, user: User) -> Client:
        client = self.get(db, client_id)
        object_name = await storage_service.upload_image(file, f"clients/{client.id}/profile-photo")
        client.photo_path = object_name
        audit_service.log(
            db,
            entity_type="client",
            entity_id=client.id,
            action="client_photo_uploaded",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"photo_path": object_name},
        )
        db.commit()
        db.refresh(client)
        self._attach_photo_url(client)
        return client

    def delete(self, db: Session, client_id: str, user: User) -> None:
        client = self.get(db, client_id)
        contract_count = db.scalar(select(func.count(Contract.id)).where(Contract.client_id == client.id)) or 0
        if contract_count > 0:
            raise AppError(
                "Este paciente já possui contratos vinculados e não pode ser excluído. Se necessário, mantenha-o como inativo.",
                409,
                "client_has_contracts",
            )

        audit_service.log(
            db,
            entity_type="client",
            entity_id=client.id,
            action="client_deleted",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.delete(client)
        db.commit()

    @staticmethod
    def _attach_photo_url(client: Client) -> Client:
        photo_path = getattr(client, "photo_path", None)
        client.photo_url = storage_service.presigned_get_url(photo_path) if photo_path else None
        return client


client_service = ClientService()
