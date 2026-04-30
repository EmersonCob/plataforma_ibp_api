from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import ClientStatus


class ClientBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    identity_number: str | None = Field(default=None, max_length=40)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    address_street: str | None = Field(default=None, max_length=220)
    address_number: str | None = Field(default=None, max_length=40)
    address_complement: str | None = Field(default=None, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    zip_code: str | None = Field(default=None, max_length=12)
    financial_responsible_name: str | None = Field(default=None, max_length=220)
    financial_responsible_cpf: str | None = Field(default=None, max_length=14)
    financial_responsible_phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=4000)
    status: ClientStatus = ClientStatus.ativo

    @field_validator(
        "cpf",
        "identity_number",
        "phone",
        "address",
        "address_street",
        "address_number",
        "address_complement",
        "neighborhood",
        "city",
        "state",
        "zip_code",
        "financial_responsible_name",
        "financial_responsible_cpf",
        "financial_responsible_phone",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    identity_number: str | None = Field(default=None, max_length=40)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    address_street: str | None = Field(default=None, max_length=220)
    address_number: str | None = Field(default=None, max_length=40)
    address_complement: str | None = Field(default=None, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    zip_code: str | None = Field(default=None, max_length=12)
    financial_responsible_name: str | None = Field(default=None, max_length=220)
    financial_responsible_cpf: str | None = Field(default=None, max_length=14)
    financial_responsible_phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=4000)
    status: ClientStatus | None = None

    @field_validator(
        "cpf",
        "identity_number",
        "phone",
        "address",
        "address_street",
        "address_number",
        "address_complement",
        "neighborhood",
        "city",
        "state",
        "zip_code",
        "financial_responsible_name",
        "financial_responsible_cpf",
        "financial_responsible_phone",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ClientStatusUpdate(BaseModel):
    status: ClientStatus


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    size: int
