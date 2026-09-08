from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def make_member_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"MED-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def make_authorisation_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"AUTH-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def make_medical_claim_number() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"MCL-{stamp}-{uuid.uuid4().hex[:8].upper()}"


class MedicalPlan(Base):
    __tablename__ = "medical_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_premium: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="LSL", server_default="LSL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    benefits: Mapped[list[MedicalBenefit]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", lazy="selectin"
    )
    members: Mapped[list[MedicalMember]] = relationship(back_populates="plan")


class MedicalBenefit(Base):
    __tablename__ = "medical_benefits"
    __table_args__ = (UniqueConstraint("plan_id", "code", name="uq_medical_benefit_plan_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_plans.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    annual_monetary_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    per_event_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    annual_visit_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_authorisation: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped[MedicalPlan] = relationship(back_populates="benefits")
    utilisations: Mapped[list[MedicalUtilisation]] = relationship(back_populates="benefit")


class MedicalMember(Base):
    __tablename__ = "medical_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_member_number
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_plans.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="active", server_default="active", index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped[MedicalPlan] = relationship(back_populates="members", lazy="joined")
    dependants: Mapped[list[MedicalDependant]] = relationship(
        back_populates="member", cascade="all, delete-orphan", lazy="selectin"
    )
    utilisations: Mapped[list[MedicalUtilisation]] = relationship(back_populates="member")
    authorisations: Mapped[list[MedicalAuthorisation]] = relationship(back_populates="member")
    claims: Mapped[list[MedicalClaim]] = relationship(back_populates="member")


class MedicalDependant(Base):
    __tablename__ = "medical_dependants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_members.id", ondelete="CASCADE"), index=True
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    relationship_type: Mapped[str] = mapped_column(String(50), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", server_default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped[MedicalMember] = relationship(back_populates="dependants")


class MedicalUtilisation(Base):
    __tablename__ = "medical_utilisations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_members.id", ondelete="CASCADE"), index=True
    )
    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_benefits.id", ondelete="RESTRICT"), index=True
    )
    dependant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_dependants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    units: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    provider_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped[MedicalMember] = relationship(back_populates="utilisations")
    benefit: Mapped[MedicalBenefit] = relationship(back_populates="utilisations", lazy="joined")


class MedicalAuthorisation(Base):
    __tablename__ = "medical_authorisations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authorisation_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_authorisation_number
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_members.id", ondelete="CASCADE"), index=True
    )
    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_benefits.id", ondelete="RESTRICT"), index=True
    )
    dependant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_dependants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    requested_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    member: Mapped[MedicalMember] = relationship(back_populates="authorisations")


class MedicalClaim(Base):
    __tablename__ = "medical_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_number: Mapped[str] = mapped_column(
        String(48), unique=True, index=True, default=make_medical_claim_number
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_members.id", ondelete="CASCADE"), index=True
    )
    dependant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_dependants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claim_kind: Mapped[str] = mapped_column(String(40), default="medical", server_default="medical", index=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", server_default="submitted", index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    member: Mapped[MedicalMember] = relationship(back_populates="claims")
