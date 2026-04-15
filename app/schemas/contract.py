from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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


class ContractBase(BaseModel):
    client_id: str
    template_id: str | None = None
    title: str = Field(min_length=3, max_length=220)
    content: str = Field(min_length=10)


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    content: str | None = Field(default=None, min_length=10)
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

