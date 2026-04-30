import os
from datetime import date

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from app.models.client import Client  # noqa: E402
from app.services.contract_rendering import (  # noqa: E402
    build_contract_snapshot_from_client,
    build_client_contract_address,
    render_contract_text,
    resolve_signer_name,
)


def test_build_snapshot_and_render_contract_text() -> None:
    client = Client(
        full_name="Maria da Silva",
        cpf="123.456.789-10",
        identity_number="MG-12.345.678",
        birth_date=date(1990, 5, 17),
        phone="(31) 99999-0000",
        address_street="Rua das Flores",
        address_number="120",
        address_complement="Apto 301",
        neighborhood="Centro",
        city="Belo Horizonte",
        state="MG",
        zip_code="30100-000",
        financial_responsible_name="Joao da Silva",
        financial_responsible_cpf="987.654.321-00",
        financial_responsible_phone="(31) 98888-1111",
    )

    snapshot = build_contract_snapshot_from_client(client)
    text = render_contract_text(snapshot)

    assert snapshot["patient"]["address"] == "Rua das Flores, 120, Apto 301, Centro - Belo Horizonte, MG / 30100-000"
    assert "Maria da Silva" in text
    assert "MG-12.345.678" in text
    assert "Joao da Silva" in text
    assert "Assinatura do Responsavel" in text


def test_resolve_signer_name_uses_selected_role() -> None:
    snapshot = {
        "patient": {"name": "Paciente Teste"},
        "financial_responsible": {"name": "Responsavel Teste"},
    }

    assert resolve_signer_name(snapshot, "paciente") == "Paciente Teste"
    assert resolve_signer_name(snapshot, "responsavel") == "Responsavel Teste"


def test_build_client_contract_address_recomputes_when_fields_change() -> None:
    client = Client(
        address="Rua Antiga, 10, Centro - Cidade, MG / 30000-000",
        address_street="Rua Nova",
        address_number="99",
        neighborhood="Savassi",
        city="Belo Horizonte",
        state="SP",
        zip_code="01000-000",
    )

    assert build_client_contract_address(client) == "Rua Nova, 99, Savassi - Belo Horizonte, SP / 01000-000"
