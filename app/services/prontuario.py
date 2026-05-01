from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import not_found
from app.models.enums import ActorType
from app.models.prontuario import ProntuarioEntry
from app.models.user import User
from app.schemas.prontuario import ProntuarioCreate, ProntuarioUpdate
from app.services.audit import audit_service


class ProntuarioService:
    def list(
        self,
        db: Session,
        *,
        client_id: str | None,
        search: str | None,
        page: int,
        size: int,
    ) -> tuple[list[ProntuarioEntry], int]:
        statement = select(ProntuarioEntry).options(joinedload(ProntuarioEntry.author)).order_by(
            ProntuarioEntry.appointment_at.desc().nullslast(),
            ProntuarioEntry.created_at.desc(),
        )
        count_statement = select(func.count(ProntuarioEntry.id))

        if client_id:
            statement = statement.where(ProntuarioEntry.client_id == client_id)
            count_statement = count_statement.where(ProntuarioEntry.client_id == client_id)

        if search:
            term = f"%{search.strip()}%"
            condition = or_(
                ProntuarioEntry.title.ilike(term),
                ProntuarioEntry.summary.ilike(term),
                ProntuarioEntry.content.ilike(term),
            )
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = db.scalar(count_statement) or 0
        items = list(db.scalars(statement.offset((page - 1) * size).limit(size)).all())
        for item in items:
            self._attach_author_name(item)
        return items, total

    def get(self, db: Session, entry_id: str) -> ProntuarioEntry:
        entry = db.scalar(
            select(ProntuarioEntry)
            .options(joinedload(ProntuarioEntry.author))
            .where(ProntuarioEntry.id == entry_id)
        )
        if not entry:
            raise not_found("Registro de prontuário não encontrado")
        self._attach_author_name(entry)
        return entry

    def create(self, db: Session, payload: ProntuarioCreate, user: User) -> ProntuarioEntry:
        entry = ProntuarioEntry(author_id=user.id, **payload.model_dump())
        db.add(entry)
        db.flush()
        audit_service.log(
            db,
            entity_type="prontuario",
            entity_id=entry.id,
            action="prontuario_created",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"client_id": entry.client_id},
        )
        db.commit()
        return self.get(db, entry.id)

    def update(self, db: Session, entry_id: str, payload: ProntuarioUpdate, user: User) -> ProntuarioEntry:
        entry = self.get(db, entry_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(entry, field, value)
        audit_service.log(
            db,
            entity_type="prontuario",
            entity_id=entry.id,
            action="prontuario_updated",
            actor_type=ActorType.admin,
            actor_id=user.id,
            metadata={"fields": list(updates.keys())},
        )
        db.commit()
        return self.get(db, entry.id)

    def delete(self, db: Session, entry_id: str, user: User) -> None:
        entry = self.get(db, entry_id)
        audit_service.log(
            db,
            entity_type="prontuario",
            entity_id=entry.id,
            action="prontuario_deleted",
            actor_type=ActorType.admin,
            actor_id=user.id,
        )
        db.delete(entry)
        db.commit()

    @staticmethod
    def _attach_author_name(entry: ProntuarioEntry) -> ProntuarioEntry:
        entry.author_name = entry.author.name if entry.author else None
        return entry


prontuario_service = ProntuarioService()
