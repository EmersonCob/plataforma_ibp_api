from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import ActorType


class AuditService:
    def log(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_type: ActorType,
        actor_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            metadata_json=metadata or {},
        )
        db.add(entry)
        return entry


audit_service = AuditService()

