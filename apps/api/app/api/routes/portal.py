import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, SuperUser
from app.models.claim import Claim
from app.models.customer import Customer
from app.models.finance import Invoice
from app.models.guarantee import Guarantee
from app.models.identity import User
from app.models.insurance import Policy
from app.models.medical import MedicalMember
from app.models.notification import Notification
from app.models.portal import CustomerPortalAccess
from app.schemas.portal import (
    PortalAccessCreate,
    PortalAccessResponse,
    PortalAccessUpdate,
    PortalCustomerSummary,
    PortalOverviewResponse,
    PortalUserSummary,
)
from app.services.audit import record_audit_event
from app.services.notifications import notify_user

router = APIRouter(prefix="/portal", tags=["customer-portal"])


async def _get_access_or_403(
    session: DbSession,
    user_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> CustomerPortalAccess:
    result = await session.execute(
        select(CustomerPortalAccess).where(
            CustomerPortalAccess.user_id == user_id,
            CustomerPortalAccess.customer_id == customer_id,
            CustomerPortalAccess.is_active.is_(True),
        )
    )
    access = result.scalar_one_or_none()
    if access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer portal access denied")
    return access


@router.get("/users", response_model=list[PortalUserSummary])
async def list_portal_candidate_users(_: SuperUser, session: DbSession):
    result = await session.execute(select(User).where(User.is_active.is_(True)).order_by(User.full_name))
    return list(result.scalars().all())


@router.get("/access", response_model=list[PortalAccessResponse])
async def list_portal_access(_: SuperUser, session: DbSession):
    result = await session.execute(
        select(CustomerPortalAccess).order_by(CustomerPortalAccess.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/access", response_model=PortalAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_portal_access(
    payload: PortalAccessCreate,
    admin: SuperUser,
    session: DbSession,
):
    user = await session.get(User, payload.user_id)
    customer = await session.get(Customer, payload.customer_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    existing_result = await session.execute(
        select(CustomerPortalAccess).where(
            CustomerPortalAccess.user_id == payload.user_id,
            CustomerPortalAccess.customer_id == payload.customer_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        if existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Portal access already exists")
        existing.is_active = True
        existing.portal_role = payload.portal_role
        existing.created_by_user_id = admin.id
        access = existing
    else:
        access = CustomerPortalAccess(
            **payload.model_dump(),
            created_by_user_id=admin.id,
        )
        session.add(access)
    await session.flush()
    await notify_user(
        session,
        user_id=user.id,
        customer_id=customer.id,
        category="portal",
        title="Customer portal access enabled",
        message=f"You now have {access.portal_role} access to {customer.display_name} in the gRisk customer portal.",
        action_url="/portal",
    )
    await record_audit_event(
        session,
        action="portal.access_granted",
        entity_type="customer_portal_access",
        entity_id=str(access.id),
        actor_user_id=admin.id,
        details={"user_id": str(user.id), "customer_id": str(customer.id), "portal_role": access.portal_role},
    )
    await session.commit()
    await session.refresh(access)
    return access


@router.patch("/access/{access_id}", response_model=PortalAccessResponse)
async def update_portal_access(
    access_id: uuid.UUID,
    payload: PortalAccessUpdate,
    admin: SuperUser,
    session: DbSession,
):
    access = await session.get(CustomerPortalAccess, access_id)
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portal access not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(access, field, value)
    await record_audit_event(
        session,
        action="portal.access_updated",
        entity_type="customer_portal_access",
        entity_id=str(access.id),
        actor_user_id=admin.id,
        details={"changed_fields": sorted(changes)},
    )
    await session.commit()
    await session.refresh(access)
    return access


@router.get("/customers", response_model=list[PortalCustomerSummary])
async def portal_customers(user: CurrentUser, session: DbSession):
    result = await session.execute(
        select(CustomerPortalAccess, Customer)
        .join(Customer, Customer.id == CustomerPortalAccess.customer_id)
        .where(
            CustomerPortalAccess.user_id == user.id,
            CustomerPortalAccess.is_active.is_(True),
        )
        .order_by(Customer.display_name)
    )
    return [
        PortalCustomerSummary(
            id=customer.id,
            customer_number=customer.customer_number,
            display_name=customer.display_name,
            customer_type=customer.customer_type,
            email=customer.email,
            phone=customer.phone,
            portal_role=access.portal_role,
        )
        for access, customer in result.all()
    ]


@router.get("/customers/{customer_id}/overview", response_model=PortalOverviewResponse)
async def portal_customer_overview(
    customer_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
):
    access = await _get_access_or_403(session, user.id, customer_id)
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    policies_result = await session.execute(
        select(Policy).where(Policy.customer_id == customer_id).order_by(Policy.created_at.desc()).limit(100)
    )
    claims_result = await session.execute(
        select(Claim).where(Claim.customer_id == customer_id).order_by(Claim.created_at.desc()).limit(100)
    )
    medical_result = await session.execute(
        select(MedicalMember).where(MedicalMember.customer_id == customer_id).order_by(MedicalMember.created_at.desc()).limit(100)
    )
    guarantees_result = await session.execute(
        select(Guarantee).where(Guarantee.customer_id == customer_id).order_by(Guarantee.created_at.desc()).limit(100)
    )
    invoices_result = await session.execute(
        select(Invoice).where(Invoice.customer_id == customer_id).order_by(Invoice.issue_date.desc()).limit(100)
    )
    outstanding = await session.scalar(
        select(func.coalesce(func.sum(Invoice.amount_due - Invoice.amount_paid), 0)).where(
            Invoice.customer_id == customer_id,
            Invoice.status.in_(["issued", "partially_paid"]),
        )
    ) or Decimal(0)
    unread = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.customer_id == customer_id,
            Notification.status == "unread",
        )
    ) or 0

    return PortalOverviewResponse(
        customer=PortalCustomerSummary(
            id=customer.id,
            customer_number=customer.customer_number,
            display_name=customer.display_name,
            customer_type=customer.customer_type,
            email=customer.email,
            phone=customer.phone,
            portal_role=access.portal_role,
        ),
        policies=list(policies_result.scalars().all()),
        claims=list(claims_result.scalars().all()),
        medical_members=list(medical_result.scalars().all()),
        guarantees=list(guarantees_result.scalars().all()),
        invoices=list(invoices_result.scalars().all()),
        outstanding_balance=outstanding,
        unread_notifications=unread,
    )
