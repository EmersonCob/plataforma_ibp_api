import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from app.core.errors import AppError  # noqa: E402
from app.models.contract import Contract  # noqa: E402
from app.models.enums import ContractStatus  # noqa: E402
from app.models.signature import Signature  # noqa: E402
from app.services.contracts import ContractService  # noqa: E402


def test_signed_contract_cannot_be_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContractService()
    contract = Contract(id="contract-id", status=ContractStatus.assinado)
    monkeypatch.setattr(service, "get", lambda _db, _contract_id: contract)

    with pytest.raises(AppError) as exc_info:
        service.delete(None, "contract-id", None)

    assert exc_info.value.code == "signed_contract_locked"


def test_contract_with_signature_cannot_be_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContractService()
    contract = Contract(id="contract-id", status=ContractStatus.aguardando_assinatura)
    contract.signature = Signature(contract_id="contract-id")
    monkeypatch.setattr(service, "get", lambda _db, _contract_id: contract)

    with pytest.raises(AppError) as exc_info:
        service.delete(None, "contract-id", None)

    assert exc_info.value.code == "signed_contract_locked"

