from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProntuarioBase(BaseModel):
    client_id: str
    title: str = Field(min_length=3, max_length=220)
    appointment_at: datetime | None = None
    summary: str | None = Field(default=None, max_length=4000)
    content: str = Field(min_length=3, max_length=20000)
    metadata_json: dict | None = None

    @field_validator("title", "summary", "content", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class ProntuarioCreate(ProntuarioBase):
    pass


class ProntuarioUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    appointment_at: datetime | None = None
    summary: str | None = Field(default=None, max_length=4000)
    content: str | None = Field(default=None, min_length=3, max_length=20000)
    metadata_json: dict | None = None

    @field_validator("title", "summary", "content", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class ProntuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    author_id: str
    author_name: str | None = None
    title: str
    appointment_at: datetime | None
    summary: str | None
    content: str
    metadata_json: dict | None = None
    created_at: datetime
    updated_at: datetime


class ProntuarioListResponse(BaseModel):
    items: list[ProntuarioRead]
    total: int
    page: int
    size: int
