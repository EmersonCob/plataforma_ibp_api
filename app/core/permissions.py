from app.models.enums import UserRole

ROLE_LEVELS: dict[UserRole, int] = {
    UserRole.usuario: 1,
    UserRole.gerente: 2,
    UserRole.adm: 5,
    UserRole.admin: 5,
}


def normalize_role(role: UserRole) -> UserRole:
    return UserRole.adm if role == UserRole.admin else role


def role_level(role: UserRole) -> int:
    return ROLE_LEVELS[role]


def public_role_value(role: UserRole) -> str:
    return normalize_role(role).value
