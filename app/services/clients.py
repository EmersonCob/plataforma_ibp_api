from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.client import Client
from app.models.enums import ActorType
from app.models.user import User
from app.repositories.clients import client_repository
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.audit import audit_service


class ClientService:
    def list(self, db: Session, *, search: str | None, page: int, size: int) -> tuple[list[Client], int]:
        return client_repository.list(db, search=search, page=page, size=size)

    def get(self, db: Session, client_id: str) -> Client:
        client = db.get(Client, client_id)
        if not client:
            raise not_found("Cliente não encontrado")
        return client

    def create(self, db: Session, payload: ClientCreate, user: User) -> Client:
        client = Client(**payload.model_dump())
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
        return client

    def update(self, db: Session, client_id: str, payload: ClientUpdate, user: User) -> Client:
        client = self.get(db, client_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(client, field, value)
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
        return client


client_service = ClientService()

