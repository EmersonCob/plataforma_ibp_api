from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import SignatureStatus


class Signature(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "signatures"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_signatures_contract_id"),
        Index("ix_signatures_signed_at", "signed_at"),
    )

    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(220), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signature_image_path: Mapped[str] = mapped_column(String(600), nullable=False)
    face_photo_path: Mapped[str] = mapped_column(String(600), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus, name="signature_status"),
        default=SignatureStatus.completed,
        nullable=False,
    )
    evidence_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    contract = relationship("Contract", back_populates="signature")

