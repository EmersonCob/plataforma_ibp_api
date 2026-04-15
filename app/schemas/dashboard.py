from datetime import datetime

from pydantic import BaseModel


class DashboardContractItem(BaseModel):
    id: str
    title: str
    client_name: str
    status: str
    created_at: datetime


class DashboardSignatureItem(BaseModel):
    id: str
    contract_id: str
    contract_title: str
    signer_name: str
    signed_at: datetime


class DashboardSummary(BaseModel):
    total_clients: int
    pending_contracts: int
    signed_contracts: int
    cancelled_or_expired_contracts: int
    latest_contracts: list[DashboardContractItem]
    latest_signatures: list[DashboardSignatureItem]

