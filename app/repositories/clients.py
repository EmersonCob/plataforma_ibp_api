from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.enums import ClientStatus


class ClientRepository:
    def list(
        self,
        db: Session,
        *,
        search: str | None,
        status: ClientStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[Client], int]:
        statement = select(Client).order_by(Client.created_at.desc())
        count_statement = select(func.count(Client.id))

        if status is not None:
            statement = statement.where(Client.status == status)
            count_statement = count_statement.where(Client.status == status)

        if search:
            normalized_search = search.strip()
            term = f"%{normalized_search}%"
            digit_term = "".join(char for char in normalized_search if char.isdigit())
            conditions = [
                Client.full_name.ilike(term),
                Client.email.ilike(term),
                Client.cpf.ilike(term),
                Client.phone.ilike(term),
                Client.city.ilike(term),
                Client.zip_code.ilike(term),
                Client.financial_responsible_name.ilike(term),
                Client.financial_responsible_cpf.ilike(term),
                Client.financial_responsible_phone.ilike(term),
            ]
            if digit_term:
                digit_like = f"%{digit_term}%"
                conditions.extend(
                    [
                        func.regexp_replace(func.coalesce(Client.cpf, ""), r"\D", "", "g").ilike(digit_like),
                        func.regexp_replace(func.coalesce(Client.phone, ""), r"\D", "", "g").ilike(digit_like),
                        func.regexp_replace(func.coalesce(Client.zip_code, ""), r"\D", "", "g").ilike(digit_like),
                        func.regexp_replace(func.coalesce(Client.financial_responsible_cpf, ""), r"\D", "", "g").ilike(digit_like),
                        func.regexp_replace(func.coalesce(Client.financial_responsible_phone, ""), r"\D", "", "g").ilike(digit_like),
                    ]
                )
            condition = or_(*conditions)
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        total = db.scalar(count_statement) or 0
        items = list(db.scalars(statement.offset((page - 1) * size).limit(size)).all())
        return items, total


client_repository = ClientRepository()
