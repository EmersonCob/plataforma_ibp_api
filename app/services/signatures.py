import logging
from datetime import UTC, datetime

from fastapi import Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError, not_found
from app.core.security import decode_data_url, now_utc
from app.models.client import Client
from app.models.contract import Contract
from app.models.enums import ActorType, ContractStatus
from app.models.signature import Signature
from app.schemas.signature import PublicSignRequest
from app.services.audit import audit_service
from app.services.contract_rendering import build_contract_snapshot_from_client, render_contract_text, resolve_signer_name
from app.services.document import document_service
from app.services.storage import storage_service

SIGNABLE_STATUSES = {
    ContractStatus.gerado,
    ContractStatus.enviado,
    ContractStatus.visualizado,
    ContractStatus.aguardando_assinatura,
}

logger = logging.getLogger(__name__)


class SignatureService:
    def get_contract_by_token(self, db: Session, token: str, *, mark_viewed: bool = False) -> Contract:
        contract = db.scalar(
            select(Contract)
            .options(joinedload(Contract.client), joinedload(Contract.signature))
            .where(Contract.generated_link_token == token)
        )
        if not contract:
            raise not_found("Link de assinatura não encontrado")
        if not contract.form_snapshot and contract.client:
            contract.form_snapshot = build_contract_snapshot_from_client(contract.client)

        if contract.link_expires_at and contract.link_expires_at < datetime.now(UTC) and contract.status != ContractStatus.assinado:
            contract.status = ContractStatus.expirado
            audit_service.log(
                db,
                entity_type="contract",
                entity_id=contract.id,
                action="public_link_expired",
                actor_type=ActorType.system,
            )
            db.commit()
            raise AppError("Este link de assinatura expirou.", 410, "signature_link_expired")

        if contract.status in {ContractStatus.cancelado, ContractStatus.expirado}:
            raise AppError("Este link de assinatura não está mais disponível.", 410, "signature_link_unavailable")

        if mark_viewed and contract.status in {ContractStatus.gerado, ContractStatus.enviado, ContractStatus.aguardando_assinatura}:
            contract.status = ContractStatus.visualizado
            audit_service.log(
                db,
                entity_type="contract",
                entity_id=contract.id,
                action="contract_public_viewed",
                actor_type=ActorType.public_signer,
            )
            db.commit()
            db.refresh(contract)

        return contract

    async def upload_photo(self, db: Session, redis: Redis, token: str, file: UploadFile) -> tuple[str, str]:
        contract = self.get_contract_by_token(db, token)
        if contract.status not in SIGNABLE_STATUSES:
            raise AppError("Este contrato não aceita novo envio de foto.", 409, "contract_not_signable")

        object_name = await storage_service.upload_image(file, f"contracts/{contract.id}/face-photos")
        await redis.setex(self._photo_key(token), 60 * 60 * 24, object_name)
        audit_service.log(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="signature_photo_uploaded",
            actor_type=ActorType.public_signer,
            metadata={"face_photo_path": object_name},
        )
        db.commit()
        return object_name, storage_service.presigned_get_url(object_name)

    async def sign(self, db: Session, redis: Redis, token: str, payload: PublicSignRequest, request: Request) -> Signature:
        lock_key = f"signature-lock:{token}"
        lock_acquired = await redis.set(lock_key, "1", ex=45, nx=True)
        if not lock_acquired:
            raise AppError("Assinatura ja esta em processamento. Aguarde alguns segundos.", 409, "signature_in_progress")

        try:
            cached_photo_path = await redis.get(self._photo_key(token))
            if cached_photo_path != payload.face_photo_path:
                raise AppError("Envie a foto de confirmação antes de assinar.", 400, "photo_required")

            contract = db.scalar(self._contract_for_signing_statement(token))
            if not contract:
                raise not_found("Link de assinatura não encontrado")
            existing_signature = db.scalar(select(Signature).where(Signature.contract_id == contract.id))
            if contract.status == ContractStatus.assinado or existing_signature:
                raise AppError("Este contrato ja foi assinado.", 409, "already_signed")
            if contract.status not in SIGNABLE_STATUSES:
                raise AppError("Este contrato não está disponível para assinatura.", 409, "contract_not_signable")
            if contract.link_expires_at and contract.link_expires_at < datetime.now(UTC):
                contract.status = ContractStatus.expirado
                raise AppError("Este link de assinatura expirou.", 410, "signature_link_expired")

            snapshot = contract.form_snapshot
            if not snapshot:
                client = db.get(Client, contract.client_id)
                if client:
                    snapshot = build_contract_snapshot_from_client(client)
                    contract.form_snapshot = snapshot
            if payload.responsible_snapshot is not None:
                responsible_payload = payload.responsible_snapshot.model_dump(mode="json")
                has_responsible_value = any((value or "").strip() for value in responsible_payload.values())
                snapshot = dict(snapshot or {})
                snapshot["financial_responsible"] = responsible_payload if has_responsible_value else None
                contract.form_snapshot = snapshot
                contract.content = render_contract_text(snapshot)

            signer_name = resolve_signer_name(snapshot, payload.signer_role)
            if not signer_name:
                raise AppError(
                    "Não foi possível identificar o assinante selecionado. Revise os dados do contrato e tente novamente.",
                    400,
                    "invalid_signer_role",
                )

            try:
                signature_bytes = decode_data_url(payload.signature_data_url)
            except ValueError as exc:
                raise AppError(
                    "Não foi possível ler a assinatura. Limpe o campo, assine novamente e tente confirmar.",
                    400,
                    "invalid_signature_image",
                ) from exc
            if len(signature_bytes) > 2 * 1024 * 1024:
                raise AppError("Assinatura maior que o limite permitido.", 413, "signature_too_large")

            signed_at = now_utc()
            signature_path = storage_service.upload_bytes(
                f"contracts/{contract.id}/signatures/signature-{signed_at.strftime('%Y%m%d%H%M%S')}.png",
                signature_bytes,
                "image/png",
            )
            signature = Signature(
                contract_id=contract.id,
                signer_name=signer_name,
                signer_role=payload.signer_role,
                signed_at=signed_at,
                signature_image_path=signature_path,
                face_photo_path=payload.face_photo_path,
                ip_address=self._client_ip(request),
                user_agent=request.headers.get("user-agent"),
                evidence_metadata={
                    "contract_version": contract.current_version,
                    "contract_title": contract.title,
                    "signed_content_sha256": self._content_hash(contract.content),
                    "signer_role": payload.signer_role,
                },
            )
            db.add(signature)
            contract.signature = signature
            contract.status = ContractStatus.assinado
            contract.signed_at = signed_at
            db.flush()
            try:
                document_service.generate_signed_pdf(db, contract)
            except AppError:
                raise
            except Exception as exc:
                logger.exception("Signed document generation failed for contract %s", contract.id)
                raise AppError(
                    "A assinatura não pode ser finalizada porque o documento assinado não foi gerado. Tente novamente em instantes.",
                    500,
                    "signed_document_generation_failed",
                ) from exc
            audit_service.log(
                db,
                entity_type="contract",
                entity_id=contract.id,
                action="contract_signed",
                actor_type=ActorType.public_signer,
                metadata={
                    "signature_id": signature.id,
                    "signed_at": signed_at.isoformat(),
                    "ip_address": signature.ip_address,
                    "signer_role": signature.signer_role,
                },
            )
            db.commit()
            await redis.delete(self._photo_key(token))
            db.refresh(signature)
            return signature
        finally:
            await redis.delete(lock_key)

    def status(self, db: Session, token: str) -> dict:
        contract = self.get_contract_by_token(db, token)
        signer_name = contract.signature.signer_name if contract.signature else None
        signer_role = contract.signature.signer_role if contract.signature else None
        return {
            "contract_id": contract.id,
            "status": contract.status,
            "signer_name": signer_name,
            "signer_role": signer_role,
            "signed_at": contract.signed_at,
        }

    @staticmethod
    def _contract_for_signing_statement(token: str):
        return select(Contract).where(Contract.generated_link_token == token).with_for_update(of=Contract)

    @staticmethod
    def _photo_key(token: str) -> str:
        return f"signature-photo:{token}"

    @staticmethod
    def _client_ip(request: Request) -> str | None:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else None

    @staticmethod
    def _content_hash(content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()


signature_service = SignatureService()
