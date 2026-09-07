from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def make_quote_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"Q-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def make_policy_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"P-{stamp}-{uuid.uuid4().hex[:8].upper()}"


class InsuranceProduct(Base):
    __tablename__ = "insurance_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    quotes: Mapped[list[Quote]] = relationship(back_populates="product")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, default=make_quote_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insurance_products.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft", server_default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    premium: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    third_party_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[InsuranceProduct] = relationship(back_populates="quotes", lazy="joined")
    items: Mapped[list[QuoteItem]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", lazy="selectin"
    )
    policy: Mapped[Policy | None] = relationship(back_populates="source_quote", uselist=False)


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote: Mapped[Quote] = relationship(back_populates="items")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, default=make_policy_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insurance_products.id", ondelete="RESTRICT"), index=True
    )
    source_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="active", server_default="active", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    premium: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source_quote: Mapped[Quote | None] = relationship(back_populates="policy")
