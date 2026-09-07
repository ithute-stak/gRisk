import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer, CustomerAddress, CustomerContact, CustomerNote
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerCreate,
    CustomerListResponse,
    CustomerNoteCreate,
    CustomerNoteResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/customers", tags=["customers"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]
CustomerTypeFilter = Annotated[str | None, Query(pattern="^(individual|company)$")]
CustomerStatusFilter = Annotated[
    str | None, Query(pattern="^(active|inactive|prospect|suspended)$")
]


def _customer_options():
    return (
        selectinload(Customer.contacts),
        selectinload(Customer.addresses),
        selectinload(Customer.notes),
    )


async def _get_customer_or_404(session: DbSession, customer_id: uuid.UUID) -> Customer:
    result = await session.execute(
        select(Customer).options(*_customer_options()).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def _derive_display_name(payload: CustomerCreate) -> str:
    if payload.display_name and payload.display_name.strip():
        return payload.display_name.strip()
    if payload.customer_type == "company":
        return (payload.company_name or "").strip()
    full_name = " ".join(part.strip() for part in (payload.first_name, payload.last_name) if part)
    return full_name.strip()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    customer_type: CustomerTypeFilter = None,
    customer_status: CustomerStatusFilter = None,
) -> CustomerListResponse:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Customer.customer_number.ilike(term),
                Customer.display_name.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
                Customer.registration_number.ilike(term),
            )
        )
    if customer_type:
        filters.append(Customer.customer_type == customer_type)
    if customer_status:
        filters.append(Customer.status == customer_status)

    total = await session.scalar(select(func.count(Customer.id)).where(*filters))
    result = await session.execute(
        select(Customer)
        .where(*filters)
        .order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return CustomerListResponse(
        items=list(result.scalars().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> Customer:
    customer = Customer(
        customer_type=payload.customer_type,
        display_name=_derive_display_name(payload),
        first_name=payload.first_name,
        last_name=payload.last_name,
        company_name=payload.company_name,
        registration_number=payload.registration_number,
        tax_number=payload.tax_number,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        status=payload.status,
        created_by_user_id=user.id,
    )
    session.add(customer)
    await session.flush()
    await record_audit_event(
        session,
        action="customer.created",
        entity_type="customer",
        entity_id=str(customer.id),
        actor_user_id=user.id,
        details={"customer_number": customer.customer_number, "display_name": customer.display_name},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _get_customer_or_404(session, customer.id)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: uuid.UUID, _: CurrentUser, session: DbSession) -> Customer:
    return await _get_customer_or_404(session, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> Customer:
    customer = await _get_customer_or_404(session, customer_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "email" and value is not None:
            value = str(value)
        setattr(customer, field, value)

    if "display_name" not in changes or not customer.display_name:
        if customer.customer_type == "company" and customer.company_name:
            customer.display_name = customer.company_name
        elif customer.customer_type == "individual":
            derived = " ".join(part for part in (customer.first_name, customer.last_name) if part)
            if derived.strip():
                customer.display_name = derived.strip()

    await record_audit_event(
        session,
        action="customer.updated",
        entity_type="customer",
        entity_id=str(customer.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(changes)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _get_customer_or_404(session, customer.id)


@router.post(
    "/{customer_id}/contacts",
    response_model=CustomerContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact(
    customer_id: uuid.UUID,
    payload: CustomerContactCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> CustomerContact:
    await _get_customer_or_404(session, customer_id)
    contact = CustomerContact(
        customer_id=customer_id,
        name=payload.name,
        role=payload.role,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
    )
    session.add(contact)
    await session.flush()
    await record_audit_event(
        session,
        action="customer.contact_added",
        entity_type="customer",
        entity_id=str(customer_id),
        actor_user_id=user.id,
        details={"contact_id": str(contact.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(contact)
    return contact


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    customer_id: uuid.UUID,
    payload: CustomerAddressCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> CustomerAddress:
    await _get_customer_or_404(session, customer_id)
    address = CustomerAddress(customer_id=customer_id, **payload.model_dump())
    session.add(address)
    await session.flush()
    await record_audit_event(
        session,
        action="customer.address_added",
        entity_type="customer",
        entity_id=str(customer_id),
        actor_user_id=user.id,
        details={"address_id": str(address.id), "address_type": address.address_type},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(address)
    return address


@router.post(
    "/{customer_id}/notes",
    response_model=CustomerNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_note(
    customer_id: uuid.UUID,
    payload: CustomerNoteCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> CustomerNote:
    await _get_customer_or_404(session, customer_id)
    note = CustomerNote(customer_id=customer_id, author_user_id=user.id, body=payload.body)
    session.add(note)
    await session.flush()
    await record_audit_event(
        session,
        action="customer.note_added",
        entity_type="customer",
        entity_id=str(customer_id),
        actor_user_id=user.id,
        details={"note_id": str(note.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(note)
    return note
