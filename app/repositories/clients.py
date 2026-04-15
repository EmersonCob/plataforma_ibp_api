from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client


class ClientRepository:
    def list(self, db: Session, *, search: str | None, page: int, size: int) -> tuple[list[Client], int]:
        statement = select(Client).order_by(Client.created_at.desc())
        count_statement = select(func.count(Client.id))

        if search:
            term = f"%{search.strip()}%"
            condition = or_(Client.full_name.ilike(term), Client.email.ilike(term), Client.cpf.ilike(term))
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = db.scalar(count_statement) or 0
        items = list(db.scalars(statement.offset((page - 1) * size).limit(size)).all())
        return items, total


client_repository = ClientRepository()

