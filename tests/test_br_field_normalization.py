import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

from app.schemas.client import ClientCreate  # noqa: E402
from app.schemas.contract import ContractPatientSnapshot, ContractResponsibleSnapshot  # noqa: E402
from app.services.contract_rendering import build_client_contract_address  # noqa: E402
from app.models.client import Client  # noqa: E402


def test_client_schema_normalizes_masked_fields() -> None:
    payload = ClientCreate(
        full_name="Paciente Teste",
        cpf="083.145.734-18",
        phone="(81) 99999-9999",
        zip_code="55780-000",
        financial_responsible_name="Responsável Teste",
        financial_responsible_cpf="123.456.789-00",
        financial_responsible_phone="(81) 98888-7777",
    )

    assert payload.cpf == "08314573418"
    assert payload.phone == "81999999999"
    assert payload.zip_code == "55780000"
    assert payload.financial_responsible_cpf == "12345678900"
    assert payload.financial_responsible_phone == "81988887777"


def test_contract_snapshots_normalize_masked_fields() -> None:
    patient = ContractPatientSnapshot(name="Paciente Teste", cpf="083.145.734-18", phone="(81) 99999-9999")
    responsible = ContractResponsibleSnapshot(name="Responsável Teste", cpf="123.456.789-00", phone="(81) 98888-7777")

    assert patient.cpf == "08314573418"
    assert patient.phone == "81999999999"
    assert responsible.cpf == "12345678900"
    assert responsible.phone == "81988887777"


def test_contract_address_formats_zip_code() -> None:
    client = Client(
        full_name="Paciente Teste",
        address_street="Avenida Central",
        address_number="547",
        address_complement="Cs",
        neighborhood="Centro",
        city="Frei Miguelinho",
        state="PE",
        zip_code="55780000",
    )

    assert build_client_contract_address(client) == "Avenida Central, 547, Cs, Centro - Frei Miguelinho, PE / 55780-000"
