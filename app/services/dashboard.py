from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.contract import Contract
from app.models.enums import ContractStatus
from app.models.signature import Signature


class DashboardService:
    def summary(self, db: Session) -> dict:
        total_clients = db.scalar(select(func.count(Client.id))) or 0
        pending_statuses = [
            ContractStatus.gerado,
            ContractStatus.enviado,
            ContractStatus.visualizado,
            ContractStatus.aguardando_assinatura,
            ContractStatus.em_edicao,
            ContractStatus.rascunho,
        ]
        pending_contracts = db.scalar(select(func.count(Contract.id)).where(Contract.status.in_(pending_statuses))) or 0
        signed_contracts = db.scalar(select(func.count(Contract.id)).where(Contract.status == ContractStatus.assinado)) or 0
        cancelled_or_expired = db.scalar(
            select(func.count(Contract.id)).where(Contract.status.in_([ContractStatus.cancelado, ContractStatus.expirado]))
        ) or 0

        latest_contracts = db.execute(
            select(Contract.id, Contract.title, Client.full_name, Contract.status, Contract.created_at)
            .join(Client)
            .order_by(Contract.created_at.desc())
            .limit(5)
        ).all()
        latest_signatures = db.execute(
            select(Signature.id, Contract.id, Contract.title, Signature.signer_name, Signature.signed_at)
            .join(Contract)
            .order_by(Signature.signed_at.desc())
            .limit(5)
        ).all()

        return {
            "total_clients": total_clients,
            "pending_contracts": pending_contracts,
            "signed_contracts": signed_contracts,
            "cancelled_or_expired_contracts": cancelled_or_expired,
            "latest_contracts": [
                {
                    "id": item.id,
                    "title": item.title,
                    "client_name": item.full_name,
                    "status": item.status.value,
                    "created_at": item.created_at,
                }
                for item in latest_contracts
            ],
            "latest_signatures": [
                {
                    "id": item.id,
                    "contract_id": item[1],
                    "contract_title": item.title,
                    "signer_name": item.signer_name,
                    "signed_at": item.signed_at,
                }
                for item in latest_signatures
            ],
        }


dashboard_service = DashboardService()

