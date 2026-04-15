from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.contract import Contract
from app.models.enums import ContractStatus


class ContractRepository:
    def list(
        self,
        db: Session,
        *,
        search: str | None,
        status: ContractStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[Contract], int]:
        statement = select(Contract).options(joinedload(Contract.client)).join(Client).order_by(Contract.created_at.desc())
        count_statement = select(func.count(Contract.id)).join(Client)

        conditions = []
        if search:
            term = f"%{search.strip()}%"
            conditions.append(or_(Contract.title.ilike(term), Client.full_name.ilike(term)))
        if status:
            conditions.append(Contract.status == status)
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = db.scalar(count_statement) or 0
        items = list(db.scalars(statement.offset((page - 1) * size).limit(size)).unique().all())
        return items, total


contract_repository = ContractRepository()

