from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ContractStatus


class ContractTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contract_templates"

    name: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    contracts = relationship("Contract", back_populates="template")


class Contract(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_status_created_at", "status", "created_at"),
        Index("ix_contracts_client_status", "client_id", "status"),
    )

    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("contract_templates.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="ibp_contract_status", inherit_schema=True),
        default=ContractStatus.rascunho,
        nullable=False,
        index=True,
    )
    generated_link_token: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_document_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    signed_document_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    form_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    client = relationship("Client", back_populates="contracts")
    template = relationship("ContractTemplate", back_populates="contracts")
    creator = relationship("User")
    versions = relationship("ContractVersion", back_populates="contract", cascade="all, delete-orphan")
    signature = relationship("Signature", back_populates="contract", uselist=False)


class ContractVersion(UUIDMixin, Base):
    __tablename__ = "contract_versions"
    __table_args__ = (
        UniqueConstraint("contract_id", "version_number", name="uq_contract_version_number"),
        Index("ix_contract_versions_contract_created", "contract_id", "created_at"),
    )

    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    contract = relationship("Contract", back_populates="versions")
    changer = relationship("User")
