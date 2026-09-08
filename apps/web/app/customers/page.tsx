"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { ActionMenu, SmartDialog } from "@/components/SmartUi";
import { apiGet, apiPost } from "@/lib/api";
import type { CustomerList, CustomerSummary } from "@/lib/types";

const emptyForm = {
  customer_type: "individual",
  first_name: "",
  last_name: "",
  company_name: "",
  registration_number: "",
  tax_number: "",
  email: "",
  phone: "",
  status: "active",
};

export default function CustomersPage() {
  const [data, setData] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (status) params.set("customer_status", status);
    if (type) params.set("customer_type", type);
    try {
      setData(await apiGet<CustomerList>(`/api/v1/customers?${params.toString()}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load customers.");
    }
  }, [search, status, type]);

  useEffect(() => { const timer = setTimeout(load, 180); return () => clearTimeout(timer); }, [load]);

  async function createCustomer(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload: Record<string, string> = {
        customer_type: form.customer_type,
        status: form.status,
      };
      for (const key of ["first_name", "last_name", "company_name", "registration_number", "tax_number", "email", "phone"] as const) {
        if (form[key].trim()) payload[key] = form[key].trim();
      }
      await apiPost<CustomerSummary>("/api/v1/customers", payload);
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create customer.");
    } finally {
      setBusy(false);
    }
  }

  function copyValue(value?: string | null) {
    if (!value || !navigator.clipboard) return;
    void navigator.clipboard.writeText(value);
  }

  return (
    <AppShell>
      <div className="page-head">
        <div><h1>Customers</h1><p>Manage individual and company customer records used across quotations, policies and claims.</p></div>
        <div className="page-actions"><button className="button" onClick={() => setShowForm(true)}>New customer</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="card">
        <div className="toolbar">
          <input className="input search" placeholder="Search name, customer number, email, phone…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 160 }} value={type} onChange={(e) => setType(e.target.value)}><option value="">All types</option><option value="individual">Individuals</option><option value="company">Companies</option></select>
          <select className="select" style={{ width: 160 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="prospect">Prospect</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option></select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Customer</th><th>Number</th><th>Type</th><th>Contact</th><th>Status</th><th>Created</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {data.items.map((customer) => (
                <tr key={customer.id}>
                  <td><div className="cell-title">{customer.display_name}</div><div className="cell-sub">{customer.email || "No email"}</div></td>
                  <td>{customer.customer_number}</td>
                  <td><span className="badge">{customer.customer_type}</span></td>
                  <td>{customer.phone || "—"}</td>
                  <td><span className={`badge ${customer.status}`}>{customer.status}</span></td>
                  <td>{new Date(customer.created_at).toLocaleDateString()}</td>
                  <td>
                    <ActionMenu label={`Actions for ${customer.display_name}`}>
                      <button type="button" className="action-menu-item" disabled={!customer.email} onClick={() => copyValue(customer.email)}>Copy email</button>
                      <button type="button" className="action-menu-item" disabled={!customer.phone} onClick={() => copyValue(customer.phone)}>Copy phone</button>
                      <button type="button" className="action-menu-item" onClick={() => copyValue(customer.customer_number)}>Copy customer number</button>
                    </ActionMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.items.length && <div className="empty"><strong>No customers found</strong>Adjust the filters or create a new customer.</div>}
        </div>
      </section>

      <SmartDialog
        open={showForm}
        onClose={() => { if (!busy) setShowForm(false); }}
        title="Create customer"
        description="Add the customer once and reuse the record across quotations, policies, claims and finance."
        size="md"
      >
        <form className="card pad" onSubmit={createCustomer}>
          <div className="form-grid">
            <div className="field"><label>Customer type</label><select className="select" value={form.customer_type} onChange={(e) => setForm({ ...form, customer_type: e.target.value })}><option value="individual">Individual</option><option value="company">Company</option></select></div>
            <div className="field"><label>Status</label><select className="select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="active">Active</option><option value="prospect">Prospect</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option></select></div>
            {form.customer_type === "company" ? (
              <><div className="field full"><label>Company name</label><input className="input" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} required /></div><div className="field"><label>Registration number</label><input className="input" value={form.registration_number} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} /></div><div className="field"><label>Tax number</label><input className="input" value={form.tax_number} onChange={(e) => setForm({ ...form, tax_number: e.target.value })} /></div></>
            ) : (
              <><div className="field"><label>First name</label><input className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div><div className="field"><label>Last name</label><input className="input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div></>
            )}
            <div className="field"><label>Email</label><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div className="field"><label>Phone</label><input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setShowForm(false)} disabled={busy}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Create customer"}</button></div>
        </form>
      </SmartDialog>
    </AppShell>
  );
}
