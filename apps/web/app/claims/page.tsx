"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Claim, ClaimEvent, ClaimList, CustomerList, Policy } from "@/lib/types";

const transitions: Record<string, string[]> = {
  reported: ["triage", "documents_pending", "rejected"],
  triage: ["documents_pending", "assessment", "rejected"],
  documents_pending: ["triage", "assessment", "rejected"],
  assessment: ["insurer_review", "approved", "rejected"],
  insurer_review: ["documents_pending", "approved", "rejected"],
  approved: ["settled"],
  rejected: ["closed"],
  settled: ["closed"],
  closed: [],
};

const emptyForm = {
  policy_id: "",
  claim_type: "general",
  incident_date: "",
  description: "",
  claim_amount: "",
  priority: "normal",
};

export default function ClaimsPage() {
  const [claims, setClaims] = useState<ClaimList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const policyMap = useMemo(() => new Map(policies.map((item) => [item.id, item])), [policies]);
  const customerMap = useMemo(() => new Map(customers.items.map((item) => [item.id, item.display_name])), [customers]);

  const load = useCallback(async () => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (status) params.set("claim_status", status);
    if (priority) params.set("priority", priority);
    setError("");
    try {
      const [claimData, policyData, customerData] = await Promise.all([
        apiGet<ClaimList>(`/api/v1/claims?${params}`),
        apiGet<Policy[]>("/api/v1/insurance/policies"),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
      ]);
      setClaims(claimData);
      setPolicies(policyData);
      setCustomers(customerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load claims.");
    }
  }, [search, status, priority]);

  useEffect(() => { const timer = setTimeout(load, 180); return () => clearTimeout(timer); }, [load]);

  async function createClaim(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<Claim>("/api/v1/claims", {
        policy_id: form.policy_id,
        claim_type: form.claim_type,
        incident_date: form.incident_date,
        description: form.description,
        claim_amount: form.claim_amount || "0",
        priority: form.priority,
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to register claim.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(claim: Claim, next: string) {
    const note = window.prompt(`Optional note for ${claim.claim_number}:`) || undefined;
    let approvedAmount: string | undefined;
    if (next === "approved") {
      const value = window.prompt(`Approved amount (claim amount ${claim.claim_amount}):`, claim.claim_amount);
      if (value === null || value.trim() === "") return;
      approvedAmount = value.trim();
    }
    setBusy(true);
    setError("");
    try {
      await apiPatch<Claim>(`/api/v1/claims/${claim.id}/status`, {
        status: next,
        note,
        approved_amount: approvedAmount,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update claim status.");
    } finally {
      setBusy(false);
    }
  }

  async function addNote(claim: Claim) {
    const note = window.prompt(`Add internal note to ${claim.claim_number}:`);
    if (!note?.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiPost<ClaimEvent>(`/api/v1/claims/${claim.id}/notes`, { note: note.trim() });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add note.");
    } finally {
      setBusy(false);
    }
  }

  const outstanding = claims.items.filter((item) => !["closed", "rejected", "settled"].includes(item.status)).length;
  const approved = claims.items.filter((item) => item.status === "approved").length;
  const totalClaimed = claims.items.reduce((sum, item) => sum + Number(item.claim_amount || 0), 0);

  return (
    <AppShell>
      <div className="page-head">
        <div><h1>Claims</h1><p>Register claims against active policies, then manage triage, assessment, insurer review, approval and settlement.</p></div>
        <div className="page-actions"><button className="button" onClick={() => setShowForm((value) => !value)}>{showForm ? "Close form" : "Register claim"}</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Claims</div><div className="value">{claims.total}</div><div className="hint">Current register</div></div>
        <div className="card metric"><div className="label">Outstanding</div><div className="value">{outstanding}</div><div className="hint">Needs operational attention</div></div>
        <div className="card metric"><div className="label">Approved</div><div className="value">{approved}</div><div className="hint">Awaiting settlement</div></div>
        <div className="card metric"><div className="label">Claimed value</div><div className="value" style={{ fontSize: "1.35rem" }}>LSL {totalClaimed.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div><div className="hint">Filtered claims</div></div>
      </section>

      {showForm && (
        <form className="card pad" onSubmit={createClaim} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Register claim</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Policy</label><select className="select" value={form.policy_id} onChange={(e) => setForm({ ...form, policy_id: e.target.value })} required><option value="">Select policy</option>{policies.map((policy) => <option key={policy.id} value={policy.id}>{policy.policy_number} · {customerMap.get(policy.customer_id) || "Customer"} · {policy.currency} {Number(policy.sum_insured).toLocaleString()}</option>)}</select></div>
            <div className="field"><label>Claim type</label><input className="input" value={form.claim_type} onChange={(e) => setForm({ ...form, claim_type: e.target.value })} required /></div>
            <div className="field"><label>Priority</label><select className="select" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option></select></div>
            <div className="field"><label>Incident date</label><input className="input" type="date" value={form.incident_date} onChange={(e) => setForm({ ...form, incident_date: e.target.value })} required /></div>
            <div className="field"><label>Claim amount</label><input className="input" type="number" min="0" step="0.01" value={form.claim_amount} onChange={(e) => setForm({ ...form, claim_amount: e.target.value })} required /></div>
            <div className="field full"><label>Description</label><textarea className="textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} minLength={5} required /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Register claim"}</button></div>
        </form>
      )}

      <section className="card">
        <div className="toolbar">
          <input className="input search" placeholder="Search claim number or description…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 180 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{Object.keys(transitions).map((item) => <option key={item}>{item}</option>)}</select>
          <select className="select" style={{ width: 150 }} value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">All priorities</option>{["low","normal","high","critical"].map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Claim</th><th>Policy / customer</th><th>Incident</th><th>Amount</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{claims.items.map((claim) => {
              const policy = policyMap.get(claim.policy_id);
              return (
                <tr key={claim.id}>
                  <td><div className="cell-title">{claim.claim_number}</div><div className="cell-sub">{claim.claim_type} · {claim.description.slice(0, 70)}{claim.description.length > 70 ? "…" : ""}</div></td>
                  <td><div>{policy?.policy_number || claim.policy_id.slice(0, 8)}</div><div className="cell-sub">{customerMap.get(claim.customer_id) || claim.customer_id.slice(0, 8)}</div></td>
                  <td>{new Date(claim.incident_date).toLocaleDateString()}</td>
                  <td className="money">LSL {Number(claim.claim_amount).toLocaleString()}</td>
                  <td><span className={`badge ${claim.priority}`}>{claim.priority}</span></td>
                  <td><span className={`badge ${claim.status}`}>{claim.status.replaceAll("_", " ")}</span></td>
                  <td><div className="actions"><button className="button ghost small" disabled={busy} onClick={() => addNote(claim)}>Add note</button>{(transitions[claim.status] || []).map((next) => <button key={next} className={next === "rejected" ? "button danger small" : "button secondary small"} disabled={busy} onClick={() => changeStatus(claim, next)}>{next.replaceAll("_", " ")}</button>)}</div></td>
                </tr>
              );
            })}</tbody>
          </table>
          {!claims.items.length && <div className="empty"><strong>No claims found</strong>Register a claim or adjust the current filters.</div>}
        </div>
      </section>
    </AppShell>
  );
}
