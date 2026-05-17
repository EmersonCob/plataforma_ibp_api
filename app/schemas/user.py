from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.core.permissions import role_level
from app.models.enums import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    email: EmailStr
    role: UserRole = UserRole.usuario
    is_active: bool = True
    can_access_contracts: bool = True
    can_access_attendance: bool = True
    can_access_prontuario: bool = True

    @field_validator("role")
    @classmethod
    def normalize_legacy_role(cls, value: UserRole) -> UserRole:
        return UserRole.adm if value == UserRole.admin else value


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=180)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    can_access_contracts: bool | None = None
    can_access_attendance: bool | None = None
    can_access_prontuario: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("role")
    @classmethod
    def normalize_legacy_role(cls, value: UserRole | None) -> UserRole | None:
        if value == UserRole.admin:
            return UserRole.adm
        return value


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def role_level(self) -> int:
        return role_level(self.role)


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    size: int


class UserDirectoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool

    @computed_field
    @property
    def role_level(self) -> int:
        return role_level(self.role)
