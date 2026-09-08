from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def make_invoice_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"INV-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def make_payment_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"PAY-{stamp}-{uuid.uuid4().hex[:8].upper()}"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_invoice_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    medical_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="draft", server_default="draft", index=True
    )
    invoice_type: Mapped[str] = mapped_column(
        String(50), default="premium", server_default="premium", index=True
    )
    description: Mapped[str] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    amount_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal(0), server_default="0"
    )
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    payments: Mapped[list[Payment]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_payment_number
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), index=True)
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
