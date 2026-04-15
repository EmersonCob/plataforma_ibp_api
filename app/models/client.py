from datetime import date

from sqlalchemy import Date, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ClientStatus


class Client(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_full_name_trgm_ready", "full_name"),
        Index("ix_clients_status_created_at", "status", "created_at"),
    )

    full_name: Mapped[str] = mapped_column(String(220), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True, unique=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, name="client_status"),
        default=ClientStatus.ativo,
        nullable=False,
        index=True,
    )

    contracts = relationship("Contract", back_populates="client")

