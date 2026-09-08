from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def make_assessment_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"RSK-{stamp}-{uuid.uuid4().hex[:8].upper()}"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_assessment_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    assessment_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    assessment_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="draft", server_default="draft", index=True
    )
    overall_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    items: Mapped[list[RiskRegisterItem]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )


class RiskRegisterItem(Base):
    __tablename__ = "risk_register_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    likelihood: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    inherent_score: Mapped[int] = mapped_column(Integer, index=True)
    inherent_level: Mapped[str] = mapped_column(String(20), index=True)
    existing_controls: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="open", server_default="open", index=True
    )
    residual_likelihood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    residual_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assessment: Mapped[RiskAssessment] = relationship(back_populates="items")
