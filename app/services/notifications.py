from abc import ABC, abstractmethod

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.contract import Contract
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notification import NotificationEvent


class BaseNotificationProvider(ABC):
    name: str

    @abstractmethod
    async def send(self, payload: dict) -> dict:
        raise NotImplementedError


class InternalNotificationProvider(BaseNotificationProvider):
    """Fallback local recorder when the channels API is not configured."""

    name = "internal_event"

    async def send(self, payload: dict) -> dict:
        return {"queued": True, "provider": self.name, "external_id": None, "payload": payload}


class ChannelsApiNotificationProvider(BaseNotificationProvider):
    name = "channels_api"

    async def send(self, payload: dict) -> dict:
        if not settings.channels_api_base_url or not settings.channels_api_internal_token:
            return await InternalNotificationProvider().send(payload)

        contact = payload.get("client") or {}
        channel_value = payload.get("channel") or NotificationChannel.whatsapp.value
        channel_type = "whatsapp" if channel_value == NotificationChannel.whatsapp.value else "webchat"
        outbound_message = payload.get("message") or "Ola, segue sua comunicacao."

        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{settings.channels_api_base_url.rstrip('/')}/internal/messages/send",
                headers={"X-Internal-Token": settings.channels_api_internal_token},
                json={
                    "channel_type": channel_type,
                    "contact_name": contact.get("name"),
                    "contact_phone": contact.get("phone"),
                    "contact_email": contact.get("email"),
                    "content": outbound_message,
                    "external_reference": payload.get("event"),
                    "metadata": payload,
                },
            )
            response.raise_for_status()
            data = response.json()

        return {
            "queued": True,
            "provider": self.name,
            "external_id": data.get("id"),
            "payload": payload,
        }


class NotificationGateway:
    def __init__(self, provider: BaseNotificationProvider | None = None) -> None:
        self.provider = provider or ChannelsApiNotificationProvider()

    def build_contract_payload(
        self,
        contract: Contract,
        event_type: str,
        channel: NotificationChannel,
        message: str | None = None,
    ) -> dict:
        sign_url = None
        if contract.generated_link_token:
            sign_url = f"{settings.public_sign_url_base.rstrip('/')}/{contract.generated_link_token}"

        first_name = (contract.client.full_name or "").strip().split(" ")[0]
        greeting_name = f", {first_name}" if first_name else ""
        default_message = message or (
            f"Ola{greeting_name}. Tudo bem?\n\n"
            "Segue o seu link para assinatura do documento IBP:"
        )
        if sign_url and sign_url not in default_message:
            default_message = f"{default_message}\n{sign_url}".strip()

        return {
            "event": event_type,
            "channel": channel.value,
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
            "message": default_message,
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
        payload = self.build_contract_payload(contract, event_type, channel, message)
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

        try:
            result = await self.provider.send(payload)
        except httpx.HTTPError as exc:
            event.status = NotificationStatus.failed
            event.provider = self.provider.name
            event.error_message = "Nao foi possivel encaminhar a mensagem para a API de canais."
            db.commit()
            raise AppError(
                "Nao foi possivel entregar a mensagem no canal configurado.",
                502,
                "notification_delivery_failed",
            ) from exc

        event.status = NotificationStatus.sent if result.get("provider") == "channels_api" else NotificationStatus.pending
        event.provider = result.get("provider") or self.provider.name
        event.external_id = result.get("external_id")

        db.commit()
        db.refresh(event)
        return event


notification_gateway = NotificationGateway()
