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
        Index("ix_clients_city_state", "city", "state"),
    )

    full_name: Mapped[str] = mapped_column(String(220), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True, unique=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_street: Mapped[str | None] = mapped_column(String(220), nullable=True)
    address_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address_complement: Mapped[str | None] = mapped_column(String(120), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    financial_responsible_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    financial_responsible_cpf: Mapped[str | None] = mapped_column(String(14), nullable=True)
    financial_responsible_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, name="ibp_client_status", inherit_schema=True),
        default=ClientStatus.ativo,
        nullable=False,
        index=True,
    )

    contracts = relationship("Contract", back_populates="client")
