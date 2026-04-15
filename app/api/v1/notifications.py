from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.enums import NotificationChannel
from app.models.user import User
from app.schemas.notification import NotificationEventRead, TriggerNotificationRequest
from app.services.contracts import contract_service
from app.services.notifications import notification_gateway
from app.core.errors import AppError

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/contracts/{contract_id}/trigger", response_model=NotificationEventRead)
async def trigger_contract_notification(
    contract_id: str,
    payload: TriggerNotificationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    contract = contract_service.get(db, contract_id)
    try:
        channel = NotificationChannel(payload.channel)
    except ValueError as exc:
        raise AppError("Canal de notificação inválido", 400, "invalid_notification_channel") from exc
    return await notification_gateway.trigger_contract_event(
        db,
        contract=contract,
        event_type=payload.event_type,
        channel=channel,
        message=payload.message,
    )
