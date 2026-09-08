"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import type { CustomerList } from "@/lib/types";
import type {
  PortalAccess,
  PortalCustomer,
  PortalOverview,
  PortalUser,
} from "@/lib/phase7-types";

const staffRoles = new Set(["superadmin", "admin", "broker", "claims", "medical", "finance", "risk", "viewer"]);
const money = new Intl.NumberFormat("en-LS", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const emptyGrant = { user_id: "", customer_id: "", portal_role: "member" };

export default function PortalPage() {
  const user = currentUser();
  const isStaff = Boolean(user?.isSuperuser || user?.roles.some((role) => staffRoles.has(role)));
  const [portalCustomers, setPortalCustomers] = useState<PortalCustomer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [overview, setOverview] = useState<PortalOverview | null>(null);
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [accessList, setAccessList] = useState<PortalAccess[]>([]);
  const [showGrant, setShowGrant] = useState(false);
  const [grantForm, setGrantForm] = useState(emptyGrant);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const userMap = useMemo(() => new Map(users.map((item) => [item.id, item])), [users]);
  const customerMap = useMemo(() => new Map(customers.items.map((item) => [item.id, item])), [customers]);

  const load = useCallback(async () => {
    setError("");
    try {
      const myCustomers = await apiGet<PortalCustomer[]>("/api/v1/portal/customers");
      setPortalCustomers(myCustomers);
      if (!selectedCustomerId && myCustomers.length) setSelectedCustomerId(myCustomers[0].id);
      if (user?.isSuperuser) {
        const [userData, customerData, accessData] = await Promise.all([
          apiGet<PortalUser[]>("/api/v1/portal/users"),
          apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
          apiGet<PortalAccess[]>("/api/v1/portal/access"),
        ]);
        setUsers(userData);
        setCustomers(customerData);
        setAccessList(accessData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load customer portal.");
    }
  }, [selectedCustomerId, user?.isSuperuser]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!selectedCustomerId) {
      setOverview(null);
      return;
    }
    let active = true;
    setError("");
    apiGet<PortalOverview>(`/api/v1/portal/customers/${selectedCustomerId}/overview`)
      .then((data) => { if (active) setOverview(data); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Unable to load portal overview."); });
    return () => { active = false; };
  }, [selectedCustomerId]);

  async function grantAccess(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<PortalAccess>("/api/v1/portal/access", grantForm);
      setGrantForm(emptyGrant);
      setShowGrant(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to grant portal access.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleAccess(access: PortalAccess) {
    setBusy(true);
    setError("");
    try {
      await apiPatch<PortalAccess>(`/api/v1/portal/access/${access.id}`, { is_active: !access.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update portal access.");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(access: PortalAccess) {
    const role = window.prompt("Portal role: owner, admin or member", access.portal_role);
    if (!role || !["owner", "admin", "member"].includes(role)) return;
    setBusy(true);
    setError("");
    try {
      await apiPatch<PortalAccess>(`/api/v1/portal/access/${access.id}`, { portal_role: role });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update portal role.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>{isStaff ? "Customer Portal" : "My Guardrisk Cover"}</h1>
          <p>{isStaff ? "Manage secure customer self-service access and inspect your own linked portal accounts." : "View your policies, claims, medical membership, guarantees, invoices and account balance securely."}</p>
        </div>
        <div className="page-actions">
          {user?.isSuperuser && <button className="button" onClick={() => setShowGrant((value) => !value)}>Grant portal access</button>}
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      {user?.isSuperuser && showGrant && (
        <form className="card pad" onSubmit={grantAccess} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Grant customer portal access</h2></div>
          <div className="form-grid">
            <div className="field full"><label>User</label><select className="select" required value={grantForm.user_id} onChange={(event) => setGrantForm({ ...grantForm, user_id: event.target.value })}><option value="">Select active user</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.email}</option>)}</select></div>
            <div className="field full"><label>Customer</label><select className="select" required value={grantForm.customer_id} onChange={(event) => setGrantForm({ ...grantForm, customer_id: event.target.value })}><option value="">Select customer</option>{customers.items.map((item) => <option key={item.id} value={item.id}>{item.customer_number} · {item.display_name}</option>)}</select></div>
            <div className="field"><label>Portal role</label><select className="select" value={grantForm.portal_role} onChange={(event) => setGrantForm({ ...grantForm, portal_role: event.target.value })}><option value="owner">Owner</option><option value="admin">Admin</option><option value="member">Member</option></select></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowGrant(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Grant access"}</button></div>
        </form>
      )}

      {user?.isSuperuser && (
        <section className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><div><h2>Portal access register</h2><p className="muted">Only explicitly linked users can view a customer through the portal.</p></div></div>
          <div className="table-wrap"><table className="table"><thead><tr><th>User</th><th>Customer</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {accessList.map((access) => {
              const portalUser = userMap.get(access.user_id);
              const customer = customerMap.get(access.customer_id);
              return <tr key={access.id}><td><strong>{portalUser?.full_name ?? access.user_id.slice(0, 8)}</strong><br /><span className="muted">{portalUser?.email ?? ""}</span></td><td>{customer?.display_name ?? access.customer_id.slice(0, 8)}</td><td>{access.portal_role}</td><td><strong>{access.is_active ? "active" : "disabled"}</strong></td><td><div className="page-actions" style={{ justifyContent: "flex-start" }}><button className="button ghost small" disabled={busy} onClick={() => changeRole(access)}>Role</button><button className="button ghost small" disabled={busy} onClick={() => toggleAccess(access)}>{access.is_active ? "Disable" : "Enable"}</button></div></td></tr>;
            })}
            {!accessList.length && <tr><td colSpan={5}><div className="empty">No customer portal access has been granted yet.</div></td></tr>}
          </tbody></table></div>
        </section>
      )}

      <section className="card pad" style={{ marginBottom: 18 }}>
        <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><div><h2>{isStaff ? "My linked customer accounts" : "Your customer accounts"}</h2><p className="muted">Portal data is scoped only to customer accounts explicitly assigned to your user.</p></div></div>
        {portalCustomers.length ? (
          <div className="field"><label>Customer account</label><select className="select" value={selectedCustomerId} onChange={(event) => setSelectedCustomerId(event.target.value)}>{portalCustomers.map((item) => <option key={item.id} value={item.id}>{item.customer_number} · {item.display_name} · {item.portal_role}</option>)}</select></div>
        ) : (
          <div className="empty">No customer account is linked to this user yet.</div>
        )}
      </section>

      {overview && (
        <>
          <section className="grid metrics" style={{ marginBottom: 20 }}>
            <div className="card metric"><div className="label">Customer</div><div className="value" style={{ fontSize: 20 }}>{overview.customer.display_name}</div><div className="hint">{overview.customer.customer_number}</div></div>
            <div className="card metric"><div className="label">Policies</div><div className="value">{overview.policies.length}</div><div className="hint">Policy records</div></div>
            <div className="card metric"><div className="label">Claims</div><div className="value">{overview.claims.length}</div><div className="hint">Claim records</div></div>
            <div className="card metric"><div className="label">Outstanding</div><div className="value">M {money.format(Number(overview.outstanding_balance))}</div><div className="hint">Issued unpaid invoices</div></div>
            <div className="card metric"><div className="label">Unread notices</div><div className="value">{overview.unread_notifications}</div><div className="hint">Customer-specific messages</div></div>
          </section>

          <section className="card" style={{ marginBottom: 18 }}><div className="card-header"><h2>Policies</h2></div><div className="table-wrap"><table className="table"><thead><tr><th>Policy</th><th>Status</th><th>Period</th><th>Sum insured</th><th>Premium</th></tr></thead><tbody>{overview.policies.map((item) => <tr key={item.id}><td>{item.policy_number}</td><td><strong>{item.status}</strong></td><td>{item.start_date} to {item.end_date}</td><td>{item.currency} {money.format(Number(item.sum_insured))}</td><td>{item.currency} {money.format(Number(item.premium))}</td></tr>)}{!overview.policies.length && <tr><td colSpan={5}>No policies recorded.</td></tr>}</tbody></table></div></section>

          <section className="card" style={{ marginBottom: 18 }}><div className="card-header"><h2>Claims</h2></div><div className="table-wrap"><table className="table"><thead><tr><th>Claim</th><th>Type</th><th>Incident</th><th>Amount</th><th>Status</th></tr></thead><tbody>{overview.claims.map((item) => <tr key={item.id}><td>{item.claim_number}</td><td>{item.claim_type}</td><td>{item.incident_date}</td><td>LSL {money.format(Number(item.claim_amount))}</td><td><strong>{item.status}</strong></td></tr>)}{!overview.claims.length && <tr><td colSpan={5}>No claims recorded.</td></tr>}</tbody></table></div></section>

          <section className="grid two" style={{ marginBottom: 18 }}>
            <div className="card"><div className="card-header"><h2>Medical aid</h2></div><div className="table-wrap"><table className="table"><thead><tr><th>Member</th><th>Status</th><th>Start</th></tr></thead><tbody>{overview.medical_members.map((item) => <tr key={item.id}><td>{item.member_number}</td><td>{item.status}</td><td>{item.start_date}</td></tr>)}{!overview.medical_members.length && <tr><td colSpan={3}>No medical membership.</td></tr>}</tbody></table></div></div>
            <div className="card"><div className="card-header"><h2>Guarantees</h2></div><div className="table-wrap"><table className="table"><thead><tr><th>Guarantee</th><th>Beneficiary</th><th>Amount</th><th>Status</th></tr></thead><tbody>{overview.guarantees.map((item) => <tr key={item.id}><td>{item.guarantee_number}</td><td>{item.beneficiary}</td><td>{item.currency} {money.format(Number(item.guarantee_amount))}</td><td>{item.status}</td></tr>)}{!overview.guarantees.length && <tr><td colSpan={4}>No guarantees recorded.</td></tr>}</tbody></table></div></div>
          </section>

          <section className="card"><div className="card-header"><div><h2>Invoices</h2><p className="muted">Billing and payment status visible to the customer.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Invoice</th><th>Description</th><th>Due</th><th>Amount</th><th>Paid</th><th>Status</th></tr></thead><tbody>{overview.invoices.map((item) => <tr key={item.id}><td>{item.invoice_number}</td><td>{item.description}</td><td>{item.due_date}</td><td>{item.currency} {money.format(Number(item.amount_due))}</td><td>{item.currency} {money.format(Number(item.amount_paid))}</td><td><strong>{item.status}</strong></td></tr>)}{!overview.invoices.length && <tr><td colSpan={6}>No invoices recorded.</td></tr>}</tbody></table></div></section>
        </>
      )}
    </AppShell>
  );
}
