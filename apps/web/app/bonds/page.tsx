"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { CustomerList, Guarantee, GuaranteeList } from "@/lib/types";

const guaranteeTypes = [
  ["bid_security", "Bid Security"],
  ["advance_payment_guarantee", "Advance Payment Guarantee"],
  ["performance_bond_guarantee", "Performance Bond Guarantee"],
  ["retention_guarantee", "Retention Guarantee"],
  ["customs_excise_bond", "Customs & Excise Bond"],
] as const;

const transitions: Record<string, string[]> = {
  draft: ["review", "cancelled"],
  review: ["draft", "submitted", "declined", "cancelled"],
  submitted: ["review", "approved", "declined", "cancelled"],
  approved: ["issued", "cancelled"],
  issued: ["released", "expired", "cancelled"],
  released: ["closed"],
  expired: ["closed"],
  declined: ["closed"],
  cancelled: ["closed"],
  closed: [],
};

const emptyForm = {
  customer_id: "",
  guarantee_type: "bid_security",
  beneficiary: "",
  principal: "",
  tender_reference: "",
  contract_reference: "",
  contract_description: "",
  contract_value: "",
  guarantee_amount: "",
  issuer_name: "",
  effective_date: "",
  expiry_date: "",
  notes: "",
};

const money = new Intl.NumberFormat("en-LS", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function typeLabel(value: string): string {
  return guaranteeTypes.find(([key]) => key === value)?.[1] ?? value.replaceAll("_", " ");
}

export default function BondsPage() {
  const [data, setData] = useState<GuaranteeList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [selected, setSelected] = useState<Guarantee | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const customerMap = useMemo(
    () => new Map(customers.items.map((item) => [item.id, item.display_name])),
    [customers],
  );

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (statusFilter) params.set("guarantee_status", statusFilter);
    if (typeFilter) params.set("guarantee_type", typeFilter);
    try {
      const [guarantees, customerData] = await Promise.all([
        apiGet<GuaranteeList>(`/api/v1/guarantees?${params.toString()}`),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
      ]);
      setData(guarantees);
      setCustomers(customerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load bonds and guarantees.");
    }
  }, [search, statusFilter, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(load, 150);
    return () => clearTimeout(timer);
  }, [load]);

  async function createGuarantee(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<Guarantee>("/api/v1/guarantees", {
        customer_id: form.customer_id,
        guarantee_type: form.guarantee_type,
        beneficiary: form.beneficiary.trim(),
        principal: form.principal.trim() || null,
        tender_reference: form.tender_reference.trim() || null,
        contract_reference: form.contract_reference.trim() || null,
        contract_description: form.contract_description.trim() || null,
        currency: "LSL",
        contract_value: form.contract_value || null,
        guarantee_amount: form.guarantee_amount,
        issuer_name: form.issuer_name.trim() || null,
        effective_date: form.effective_date || null,
        expiry_date: form.expiry_date || null,
        notes: form.notes.trim() || null,
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create guarantee.");
    } finally {
      setBusy(false);
    }
  }

  async function openGuarantee(item: Guarantee) {
    setBusy(true);
    setError("");
    try {
      setSelected(await apiGet<Guarantee>(`/api/v1/guarantees/${item.id}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open guarantee.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(item: Guarantee, next: string) {
    const note = window.prompt(`Optional note for ${item.guarantee_number}:`, "");
    if (note === null) return;
    setBusy(true);
    setError("");
    try {
      const updated = await apiPatch<Guarantee>(`/api/v1/guarantees/${item.id}/status`, {
        status: next,
        note: note.trim() || null,
      });
      if (selected?.id === item.id) setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change guarantee status.");
    } finally {
      setBusy(false);
    }
  }

  async function prepareIssuance(item: Guarantee) {
    const issuerName = window.prompt("Issuer name:", item.issuer_name ?? "Guardrisk Insurance Brokers");
    if (!issuerName?.trim()) return;
    const effectiveDate = window.prompt("Effective date (YYYY-MM-DD):", item.effective_date ?? "");
    if (!effectiveDate?.trim()) return;
    const expiryDate = window.prompt("Expiry date (YYYY-MM-DD):", item.expiry_date ?? "");
    if (!expiryDate?.trim()) return;
    setBusy(true);
    setError("");
    try {
      const updated = await apiPatch<Guarantee>(`/api/v1/guarantees/${item.id}`, {
        issuer_name: issuerName.trim(),
        effective_date: effectiveDate.trim(),
        expiry_date: expiryDate.trim(),
      });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to prepare issuance details.");
    } finally {
      setBusy(false);
    }
  }

  const activeExposure = data.items
    .filter((item) => !["closed", "declined", "cancelled"].includes(item.status))
    .reduce((sum, item) => sum + Number(item.guarantee_amount || 0), 0);
  const issued = data.items.filter((item) => item.status === "issued").length;
  const approvals = data.items.filter((item) => ["review", "submitted", "approved"].includes(item.status)).length;
  const expiring = data.items.filter((item) => {
    if (!item.expiry_date || ["closed", "released", "expired", "cancelled"].includes(item.status)) return false;
    const days = (new Date(item.expiry_date).getTime() - Date.now()) / 86400000;
    return days >= 0 && days <= 30;
  }).length;

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Bonds & Guarantees</h1>
          <p>Manage bid securities, advance-payment guarantees, performance bonds, retention guarantees and customs or excise bonds.</p>
        </div>
        <div className="page-actions">
          <button className="button" onClick={() => setShowForm((value) => !value)}>New guarantee</button>
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Guarantees</div><div className="value">{data.total}</div><div className="hint">Applications and issued instruments</div></div>
        <div className="card metric"><div className="label">Active exposure</div><div className="value">M {money.format(activeExposure)}</div><div className="hint">Open guarantee amount</div></div>
        <div className="card metric"><div className="label">Issued</div><div className="value">{issued}</div><div className="hint">Currently issued guarantees</div></div>
        <div className="card metric"><div className="label">Awaiting decision</div><div className="value">{approvals}</div><div className="hint">Review, submitted or approved</div></div>
        <div className="card metric"><div className="label">Expiring in 30 days</div><div className="value">{expiring}</div><div className="hint">Requires follow-up</div></div>
      </section>

      {showForm && (
        <form className="card pad" onSubmit={createGuarantee} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Create guarantee application</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Customer</label><select className="select" value={form.customer_id} onChange={(event) => setForm({ ...form, customer_id: event.target.value })} required><option value="">Select customer</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.customer_number} · {customer.display_name}</option>)}</select></div>
            <div className="field"><label>Guarantee type</label><select className="select" value={form.guarantee_type} onChange={(event) => setForm({ ...form, guarantee_type: event.target.value })}>{guaranteeTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <div className="field"><label>Beneficiary</label><input className="input" value={form.beneficiary} onChange={(event) => setForm({ ...form, beneficiary: event.target.value })} required /></div>
            <div className="field"><label>Principal</label><input className="input" value={form.principal} onChange={(event) => setForm({ ...form, principal: event.target.value })} /></div>
            <div className="field"><label>Tender reference</label><input className="input" value={form.tender_reference} onChange={(event) => setForm({ ...form, tender_reference: event.target.value })} /></div>
            <div className="field"><label>Contract reference</label><input className="input" value={form.contract_reference} onChange={(event) => setForm({ ...form, contract_reference: event.target.value })} /></div>
            <div className="field"><label>Contract value (LSL)</label><input className="input" type="number" min="0" step="0.01" value={form.contract_value} onChange={(event) => setForm({ ...form, contract_value: event.target.value })} /></div>
            <div className="field"><label>Guarantee amount (LSL)</label><input className="input" type="number" min="0" step="0.01" value={form.guarantee_amount} onChange={(event) => setForm({ ...form, guarantee_amount: event.target.value })} required /></div>
            <div className="field"><label>Issuer name</label><input className="input" value={form.issuer_name} onChange={(event) => setForm({ ...form, issuer_name: event.target.value })} placeholder="Can be completed before issuance" /></div>
            <div className="field"><label>Effective date</label><input className="input" type="date" value={form.effective_date} onChange={(event) => setForm({ ...form, effective_date: event.target.value })} /></div>
            <div className="field"><label>Expiry date</label><input className="input" type="date" value={form.expiry_date} onChange={(event) => setForm({ ...form, expiry_date: event.target.value })} /></div>
            <div className="field full"><label>Contract description</label><textarea className="textarea" value={form.contract_description} onChange={(event) => setForm({ ...form, contract_description: event.target.value })} /></div>
            <div className="field full"><label>Notes</label><textarea className="textarea" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Create guarantee"}</button></div>
        </form>
      )}

      <section className="card" style={{ marginBottom: 18 }}>
        <div className="card-header"><div><h2>Guarantee register</h2><p className="muted">Search and control the full guarantee lifecycle.</p></div></div>
        <div className="toolbar">
          <input className="input" placeholder="Search number, beneficiary or reference" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select className="select" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="">All types</option>{guaranteeTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select className="select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{Object.keys(transitions).map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Guarantee</th><th>Customer</th><th>Type</th><th>Beneficiary</th><th>Amount</th><th>Status</th><th>Expiry</th><th>Action</th></tr></thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td><button className="link-button" onClick={() => openGuarantee(item)}>{item.guarantee_number}</button></td>
                  <td>{customerMap.get(item.customer_id) ?? item.customer_id.slice(0, 8)}</td>
                  <td>{typeLabel(item.guarantee_type)}</td>
                  <td>{item.beneficiary}</td>
                  <td>{item.currency} {money.format(Number(item.guarantee_amount))}</td>
                  <td><strong>{item.status.replaceAll("_", " ")}</strong></td>
                  <td>{item.expiry_date ?? "-"}</td>
                  <td><button className="button ghost small" onClick={() => openGuarantee(item)}>Open</button></td>
                </tr>
              ))}
              {!data.items.length && <tr><td colSpan={8}><div className="empty">No guarantees match the current filters.</div></td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {selected && (
        <section className="card pad">
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}>
            <div><h2>{selected.guarantee_number}</h2><p className="muted">{typeLabel(selected.guarantee_type)} · {customerMap.get(selected.customer_id) ?? "Customer"}</p></div>
            <button className="button ghost small" onClick={() => setSelected(null)}>Close</button>
          </div>
          <div className="grid two" style={{ marginBottom: 18 }}>
            <div><div className="label">Beneficiary</div><strong>{selected.beneficiary}</strong></div>
            <div><div className="label">Principal</div><strong>{selected.principal ?? "-"}</strong></div>
            <div><div className="label">Guarantee amount</div><strong>{selected.currency} {money.format(Number(selected.guarantee_amount))}</strong></div>
            <div><div className="label">Contract value</div><strong>{selected.contract_value ? `${selected.currency} ${money.format(Number(selected.contract_value))}` : "-"}</strong></div>
            <div><div className="label">Issuer</div><strong>{selected.issuer_name ?? "Not set"}</strong></div>
            <div><div className="label">Period</div><strong>{selected.effective_date ?? "-"} to {selected.expiry_date ?? "-"}</strong></div>
          </div>
          {selected.contract_description && <p>{selected.contract_description}</p>}
          <div className="page-actions" style={{ justifyContent: "flex-start", marginBottom: 18 }}>
            {["approved", "review", "submitted", "draft"].includes(selected.status) && <button className="button secondary" disabled={busy} onClick={() => prepareIssuance(selected)}>Set issuance details</button>}
            {(transitions[selected.status] ?? []).map((next) => <button key={next} className="button" disabled={busy} onClick={() => changeStatus(selected, next)}>{next.replaceAll("_", " ")}</button>)}
          </div>
          <div className="card-header" style={{ paddingLeft: 0, paddingRight: 0 }}><h3>Workflow history</h3></div>
          <div className="table-wrap">
            <table className="table"><thead><tr><th>Date</th><th>Event</th><th>Transition</th><th>Note</th></tr></thead><tbody>
              {(selected.events ?? []).map((event) => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.event_type}</td><td>{event.from_status ?? "-"} → {event.to_status ?? "-"}</td><td>{event.note ?? "-"}</td></tr>)}
              {!selected.events?.length && <tr><td colSpan={4}>No workflow events recorded.</td></tr>}
            </tbody></table>
          </div>
        </section>
      )}
    </AppShell>
  );
}
