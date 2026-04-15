from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import ClientStatus


class ClientBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    status: ClientStatus = ClientStatus.ativo

    @field_validator("cpf", "phone", mode="before")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=220)
    cpf: str | None = Field(default=None, max_length=14)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    status: ClientStatus | None = None


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

