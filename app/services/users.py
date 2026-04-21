from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.core.permissions import normalize_role, role_level
from app.core.security import hash_password
from app.models.enums import ActorType, UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit import audit_service
from app.services.email import email_service


class UserService:
    def list(self, db: Session, *, search: str | None, page: int, size: int) -> tuple[list[User], int]:
        statement = select(User).order_by(User.created_at.desc())
        count_statement = select(func.count(User.id))

        if search:
            term = f"%{search.strip()}%"
            condition = or_(User.name.ilike(term), User.email.ilike(term))
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = db.scalar(count_statement) or 0
        items = list(db.scalars(statement.offset((page - 1) * size).limit(size)).all())
        return items, total

    def get(self, db: Session, user_id: str) -> User:
        user = db.get(User, user_id)
        if not user:
            raise not_found("Usuário não encontrado")
        return user

    def create(self, db: Session, payload: UserCreate, actor: User) -> User:
        role = normalize_role(payload.role)
        self._ensure_can_assign_role(actor, role)
        email = str(payload.email).lower()
        if db.scalar(select(User).where(User.email == email)):
            raise AppError("Já existe um usuário cadastrado com este e-mail.", 409, "user_email_exists")

        user = User(
            name=payload.name.strip(),
            email=email,
            password_hash=hash_password(payload.password),
            role=role,
            is_active=payload.is_active,
        )
        db.add(user)
        db.flush()
        audit_service.log(
            db,
            entity_type="user",
            entity_id=user.id,
            action="user_created",
            actor_type=ActorType.admin,
            actor_id=actor.id,
            metadata={"role": role.value},
        )
        db.commit()
        db.refresh(user)
        email_service.send_welcome_email(user, payload.password)
        return user

    def update(self, db: Session, user_id: str, payload: UserUpdate, actor: User) -> User:
        user = self.get(db, user_id)
        self._ensure_can_manage_user(actor, user)

        updates = payload.model_dump(exclude_unset=True)
        if "email" in updates and updates["email"]:
            email = str(updates["email"]).lower()
            existing = db.scalar(select(User).where(User.email == email, User.id != user.id))
            if existing:
                raise AppError("Já existe um usuário cadastrado com este e-mail.", 409, "user_email_exists")
            user.email = email

        if "name" in updates and updates["name"]:
            user.name = updates["name"].strip()

        if "role" in updates and updates["role"]:
            role = normalize_role(updates["role"])
            if user.id == actor.id and role != normalize_role(user.role):
                raise AppError("Você não pode alterar o próprio perfil de acesso.", 409, "self_role_change_not_allowed")
            self._ensure_can_assign_role(actor, role)
            user.role = role

        if "is_active" in updates and updates["is_active"] is not None:
            if user.id == actor.id and updates["is_active"] is False:
                raise AppError("Você não pode desativar o próprio acesso.", 409, "self_deactivation_not_allowed")
            user.is_active = updates["is_active"]

        if updates.get("password"):
            user.password_hash = hash_password(updates["password"])

        audit_service.log(
            db,
            entity_type="user",
            entity_id=user.id,
            action="user_updated",
            actor_type=ActorType.admin,
            actor_id=actor.id,
            metadata={"fields": [field for field in updates.keys() if field != "password"]},
        )
        db.commit()
        db.refresh(user)
        return user

    def update_status(self, db: Session, user_id: str, is_active: bool, actor: User) -> User:
        return self.update(db, user_id, UserUpdate(is_active=is_active), actor)

    def _ensure_can_manage_user(self, actor: User, target: User) -> None:
        actor_level = role_level(actor.role)
        target_level = role_level(target.role)
        if actor_level < 2:
            raise AppError("Permissão insuficiente para gerenciar usuários.", 403, "insufficient_permission")
        if actor_level < 3 and target_level >= 3:
            raise AppError("Gerentes não podem alterar acessos administrativos.", 403, "admin_user_protected")

    def _ensure_can_assign_role(self, actor: User, role: UserRole) -> None:
        actor_level = role_level(actor.role)
        target_level = role_level(role)
        if actor_level < 2:
            raise AppError("Permissão insuficiente para criar usuários.", 403, "insufficient_permission")
        if target_level >= 3 and actor_level < 3:
            raise AppError("Somente administradores podem criar acessos ADM.", 403, "admin_role_required")
        if target_level > actor_level:
            raise AppError("Você não pode atribuir um nível de acesso maior que o seu.", 403, "role_above_actor")


user_service = UserService()
