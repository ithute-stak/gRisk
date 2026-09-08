from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def make_guarantee_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"GRT-{stamp}-{uuid.uuid4().hex[:8].upper()}"


class Guarantee(Base):
    __tablename__ = "guarantees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guarantee_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_guarantee_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    guarantee_type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="draft", server_default="draft", index=True
    )
    beneficiary: Mapped[str] = mapped_column(String(200))
    principal: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tender_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    contract_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    contract_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    guarantee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    issuer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[GuaranteeEvent]] = relationship(
        back_populates="guarantee", cascade="all, delete-orphan", lazy="selectin"
    )


class GuaranteeEvent(Base):
    __tablename__ = "guarantee_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guarantee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guarantees.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guarantee: Mapped[Guarantee] = relationship(back_populates="events")
