from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.contract import Contract
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notification import NotificationEvent


class BaseNotificationProvider(ABC):
    name: str

    @abstractmethod
    async def send(self, payload: dict) -> dict:
        raise NotImplementedError


class WhatsAppProviderInterface(BaseNotificationProvider):
    pass


class InternalNotificationProvider(WhatsAppProviderInterface):
    """No external provider is called now; the event is only recorded for future dispatch."""

    name = "internal_event"

    async def send(self, payload: dict) -> dict:
        return {"queued": True, "provider": self.name, "external_id": None, "payload": payload}


class NotificationGateway:
    def __init__(self, provider: BaseNotificationProvider | None = None) -> None:
        self.provider = provider or InternalNotificationProvider()

    def build_contract_payload(self, contract: Contract, event_type: str, message: str | None = None) -> dict:
        sign_url = None
        if contract.generated_link_token:
            sign_url = f"{settings.public_sign_url_base.rstrip('/')}/{contract.generated_link_token}"

        return {
            "event": event_type,
            "client": {
                "id": contract.client.id,
                "name": contract.client.full_name,
                "phone": contract.client.phone,
                "email": contract.client.email,
            },
            "contract": {
                "id": contract.id,
                "title": contract.title,
                "status": contract.status.value,
                "sign_url": sign_url,
            },
            "message": message or "Ola, segue seu link para assinatura.",
        }

    async def trigger_contract_event(
        self,
        db: Session,
        *,
        contract: Contract,
        event_type: str,
        channel: NotificationChannel = NotificationChannel.whatsapp,
        message: str | None = None,
    ) -> NotificationEvent:
        payload = self.build_contract_payload(contract, event_type, message)
        event = NotificationEvent(
            contract_id=contract.id,
            client_id=contract.client_id,
            channel=channel,
            event_type=event_type,
            payload=payload,
            status=NotificationStatus.pending,
            provider=self.provider.name,
        )
        db.add(event)
        db.flush()

        result = await self.provider.send(payload)
        event.status = NotificationStatus.pending
        event.provider = result.get("provider") or self.provider.name
        event.external_id = result.get("external_id")

        db.commit()
        db.refresh(event)
        return event


notification_gateway = NotificationGateway()
