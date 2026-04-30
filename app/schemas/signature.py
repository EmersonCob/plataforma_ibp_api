from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.models.enums import ContractStatus
from app.schemas.contract import ContractFormSnapshot


class PublicContractRead(BaseModel):
    id: str
    title: str
    content: str
    form_snapshot: ContractFormSnapshot | None
    status: ContractStatus
    client_name: str
    link_expires_at: datetime | None
    signed_at: datetime | None


class UploadPhotoResponse(BaseModel):
    face_photo_path: str
    face_photo_url: str


class PublicSignRequest(BaseModel):
    signer_role: Literal["paciente", "responsavel"]
    face_photo_path: str = Field(min_length=3, max_length=600)
    signature_data_url: str = Field(min_length=200)


class SignatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    signer_name: str
    signer_role: str | None
    signed_at: datetime
    signature_image_path: str
    face_photo_path: str
    ip_address: str | None
    user_agent: str | None
    status: str
    evidence_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class PublicSignatureStatus(BaseModel):
    contract_id: str
    status: ContractStatus
    signer_name: str | None = None
    signer_role: str | None = None
    signed_at: datetime | None = None
