import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import User


@pytest.mark.asyncio
async def test_finance_portal_and_notification_lifecycle() -> None:
    admin_password = "Testing-Only-Strong-Password-42"
    portal_password = "Portal-Testing-Only-Password-43"
    admin_email = f"finance-admin-{uuid.uuid4().hex}@example.com"
    portal_email = f"portal-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        admin = User(
            email=admin_email,
            full_name="Finance Test Admin",
            password_hash=hash_password(admin_password),
            is_active=True,
            is_superuser=True,
        )
        portal_user = User(
            email=portal_email,
            full_name="Portal Test User",
            password_hash=hash_password(portal_password),
            is_active=True,
            is_superuser=False,
        )
        customer = Customer(
            customer_type="company",
            display_name="Portal Finance Test Company",
            company_name="Portal Finance Test Company",
            email=f"customer-{uuid.uuid4().hex}@example.com",
            status="active",
        )
        session.add_all([admin, portal_user, customer])
        await session.commit()
        admin_id = admin.id
        portal_user_id = portal_user.id
        customer_id = customer.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_email, "password": admin_password},
        )
        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        portal_login = await client.post(
            "/api/v1/auth/login",
            data={"username": portal_email, "password": portal_password},
        )
        assert portal_login.status_code == 200
        portal_headers = {"Authorization": f"Bearer {portal_login.json()['access_token']}"}

        grant = await client.post(
            "/api/v1/portal/access",
            headers=admin_headers,
            json={
                "user_id": str(portal_user_id),
                "customer_id": str(customer_id),
                "portal_role": "owner",
            },
        )
        assert grant.status_code == 201
        assert grant.json()["portal_role"] == "owner"

        portal_customers = await client.get("/api/v1/portal/customers", headers=portal_headers)
        assert portal_customers.status_code == 200
        assert any(item["id"] == str(customer_id) for item in portal_customers.json())

        portal_notifications = await client.get("/api/v1/notifications", headers=portal_headers)
        assert portal_notifications.status_code == 200
        assert portal_notifications.json()["unread"] >= 1
        assert any(
            item["category"] == "portal" for item in portal_notifications.json()["items"]
        )

        invoice_response = await client.post(
            "/api/v1/finance/invoices",
            headers=admin_headers,
            json={
                "customer_id": str(customer_id),
                "invoice_type": "premium",
                "description": "Annual insurance premium test invoice",
                "currency": "LSL",
                "amount_due": "1000.00",
                "issue_date": "2026-09-08",
                "due_date": "2026-09-30",
            },
        )
        assert invoice_response.status_code == 201
        invoice = invoice_response.json()
        assert invoice["invoice_number"].startswith("INV-")
        assert invoice["status"] == "draft"
        assert invoice["amount_paid"] == "0.00"

        issue_response = await client.patch(
            f"/api/v1/finance/invoices/{invoice['id']}/status",
            headers=admin_headers,
            json={"status": "issued"},
        )
        assert issue_response.status_code == 200
        assert issue_response.json()["status"] == "issued"

        dashboard = await client.get("/api/v1/finance/dashboard", headers=admin_headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["outstanding_balance"] == "1000.00"

        overview = await client.get(
            f"/api/v1/portal/customers/{customer_id}/overview",
            headers=portal_headers,
        )
        assert overview.status_code == 200
        assert overview.json()["customer"]["portal_role"] == "owner"
        assert overview.json()["outstanding_balance"] == "1000.00"
        assert any(item["id"] == invoice["id"] for item in overview.json()["invoices"])

        partial_payment = await client.post(
            "/api/v1/finance/payments",
            headers=admin_headers,
            json={
                "invoice_id": invoice["id"],
                "amount": "400.00",
                "payment_date": "2026-09-10",
                "payment_method": "bank_transfer",
                "reference": "TEST-PARTIAL-001",
            },
        )
        assert partial_payment.status_code == 201
        assert partial_payment.json()["payment_number"].startswith("PAY-")

        after_partial = await client.get(
            f"/api/v1/finance/invoices/{invoice['id']}",
            headers=admin_headers,
        )
        assert after_partial.status_code == 200
        assert after_partial.json()["status"] == "partially_paid"
        assert after_partial.json()["amount_paid"] == "400.00"
        assert len(after_partial.json()["payments"]) == 1

        final_payment = await client.post(
            "/api/v1/finance/payments",
            headers=admin_headers,
            json={
                "invoice_id": invoice["id"],
                "amount": "600.00",
                "payment_date": "2026-09-11",
                "payment_method": "bank_transfer",
                "reference": "TEST-FINAL-001",
            },
        )
        assert final_payment.status_code == 201

        paid_invoice = await client.get(
            f"/api/v1/finance/invoices/{invoice['id']}",
            headers=admin_headers,
        )
        assert paid_invoice.status_code == 200
        assert paid_invoice.json()["status"] == "paid"
        assert paid_invoice.json()["amount_paid"] == "1000.00"
        assert len(paid_invoice.json()["payments"]) == 2

        overpayment = await client.post(
            "/api/v1/finance/payments",
            headers=admin_headers,
            json={
                "invoice_id": invoice["id"],
                "amount": "1.00",
                "payment_date": "2026-09-11",
                "payment_method": "cash",
            },
        )
        assert overpayment.status_code == 409

        final_dashboard = await client.get("/api/v1/finance/dashboard", headers=admin_headers)
        assert final_dashboard.status_code == 200
        assert final_dashboard.json()["total_received"] == "1000.00"
        assert final_dashboard.json()["outstanding_balance"] == "0.00"

        final_overview = await client.get(
            f"/api/v1/portal/customers/{customer_id}/overview",
            headers=portal_headers,
        )
        assert final_overview.status_code == 200
        assert final_overview.json()["outstanding_balance"] == "0.00"
        assert final_overview.json()["invoices"][0]["status"] == "paid"

        notifications_after_finance = await client.get(
            "/api/v1/notifications",
            headers=portal_headers,
        )
        assert notifications_after_finance.status_code == 200
        assert notifications_after_finance.json()["unread"] >= 4
        assert any(
            item["category"] == "finance" for item in notifications_after_finance.json()["items"]
        )

        read_all = await client.patch("/api/v1/notifications/read-all", headers=portal_headers)
        assert read_all.status_code == 200
        assert read_all.json()["unread"] == 0

        direct_notification = await client.post(
            "/api/v1/notifications",
            headers=admin_headers,
            json={
                "user_id": str(portal_user_id),
                "customer_id": str(customer_id),
                "category": "general",
                "title": "Test customer message",
                "message": "A direct customer notification for lifecycle testing.",
                "action_url": "/portal",
            },
        )
        assert direct_notification.status_code == 201

        forbidden_access = await client.post(
            "/api/v1/portal/access",
            headers=portal_headers,
            json={
                "user_id": str(admin_id),
                "customer_id": str(customer_id),
                "portal_role": "member",
            },
        )
        assert forbidden_access.status_code == 403
