from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ProntuarioEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "prontuario_entries"
    __table_args__ = (
        Index("ix_prontuario_entries_client_created", "client_id", "created_at"),
        Index("ix_prontuario_entries_author_created", "author_id", "created_at"),
        Index("ix_prontuario_entries_appointment_at", "appointment_at"),
    )

    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    appointment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    client = relationship("Client")
    author = relationship("User")
