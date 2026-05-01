from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContractStatus
from app.schemas.client import ClientRead


class ContractTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ContractPatientSnapshot(BaseModel):
    name: str = Field(min_length=3, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=400)

    @field_validator("name", "cpf", "phone", "address", mode="before")
    @classmethod
    def strip_value(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class ContractResponsibleSnapshot(BaseModel):
    name: str | None = Field(default=None, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=40)

    @field_validator("name", "cpf", "phone", mode="before")
    @classmethod
    def strip_value(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class ContractFormSnapshot(BaseModel):
    patient: ContractPatientSnapshot
    financial_responsible: ContractResponsibleSnapshot | None = None


class ContractBase(BaseModel):
    client_id: str
    template_id: str | None = None
    title: str = Field(min_length=3, max_length=220)
    content: str | None = Field(default=None, min_length=10)
    form_snapshot: ContractFormSnapshot


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    content: str | None = Field(default=None, min_length=10)
    form_snapshot: ContractFormSnapshot | None = None
    status: ContractStatus | None = None


class GenerateLinkRequest(BaseModel):
    expires_at: datetime | None = None
    trigger_notification: bool = False


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    template_id: str | None
    title: str
    content: str
    current_version: int
    status: ContractStatus
    generated_link_token: str | None
    link_expires_at: datetime | None
    signed_at: datetime | None
    signed_document_path: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    form_snapshot: ContractFormSnapshot | None = None
    client: ClientRead | None = None


class ContractListResponse(BaseModel):
    items: list[ContractRead]
    total: int
    page: int
    size: int


class ContractVersionCreate(BaseModel):
    content: str = Field(min_length=10)


class ContractVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    version_number: int
    content: str
    changed_by: str
    metadata_json: dict | None = None
    created_at: datetime


class SignLinkResponse(BaseModel):
    token: str
    sign_url: str
    expires_at: datetime | None


class SignedDocumentResponse(BaseModel):
    contract_id: str
    signed_document_path: str
    signed_document_url: str
    signed_document_hash: str | None = None
    generated_at: datetime | None = None
