from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TriggerNotificationRequest(BaseModel):
    event_type: str = "contract_link_generated"
    channel: str = "whatsapp"
    message: str | None = None


class NotificationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str | None
    client_id: str | None
    channel: str
    event_type: str
    payload: dict
    status: str
    provider: str | None
    external_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

