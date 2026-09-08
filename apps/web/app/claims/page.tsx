"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { ActionMenu, SmartDialog } from "@/components/SmartUi";
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
  const [workflowTarget, setWorkflowTarget] = useState<{ claim: Claim; next: string } | null>(null);
  const [workflowNote, setWorkflowNote] = useState("");
  const [approvedAmount, setApprovedAmount] = useState("");
  const [noteTarget, setNoteTarget] = useState<Claim | null>(null);
  const [noteText, setNoteText] = useState("");
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

  function beginStatusChange(claim: Claim, next: string) {
    setWorkflowTarget({ claim, next });
    setWorkflowNote("");
    setApprovedAmount(next === "approved" ? claim.claim_amount : "");
  }

  async function submitStatusChange(event: FormEvent) {
    event.preventDefault();
    if (!workflowTarget) return;
    const { claim, next } = workflowTarget;
    if (next === "approved" && !approvedAmount.trim()) return;

    setBusy(true);
    setError("");
    try {
      await apiPatch<Claim>(`/api/v1/claims/${claim.id}/status`, {
        status: next,
        note: workflowNote.trim() || undefined,
        approved_amount: next === "approved" ? approvedAmount.trim() : undefined,
      });
      setWorkflowTarget(null);
      setWorkflowNote("");
      setApprovedAmount("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update claim status.");
    } finally {
      setBusy(false);
    }
  }

  async function submitNote(event: FormEvent) {
    event.preventDefault();
    if (!noteTarget || !noteText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiPost<ClaimEvent>(`/api/v1/claims/${noteTarget.id}/notes`, { note: noteText.trim() });
      setNoteTarget(null);
      setNoteText("");
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
        <div className="page-actions"><button className="button" onClick={() => setShowForm(true)}>Register claim</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Claims</div><div className="value">{claims.total}</div><div className="hint">Current register</div></div>
        <div className="card metric"><div className="label">Outstanding</div><div className="value">{outstanding}</div><div className="hint">Needs operational attention</div></div>
        <div className="card metric"><div className="label">Approved</div><div className="value">{approved}</div><div className="hint">Awaiting settlement</div></div>
        <div className="card metric"><div className="label">Claimed value</div><div className="value" style={{ fontSize: "1.35rem" }}>LSL {totalClaimed.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div><div className="hint">Filtered claims</div></div>
      </section>

      <section className="card">
        <div className="toolbar">
          <input className="input search" placeholder="Search claim number or description…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 180 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{Object.keys(transitions).map((item) => <option key={item}>{item}</option>)}</select>
          <select className="select" style={{ width: 150 }} value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">All priorities</option>{["low","normal","high","critical"].map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Claim</th><th>Policy / customer</th><th>Incident</th><th>Amount</th><th>Priority</th><th>Status</th><th aria-label="Actions" /></tr></thead>
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
                  <td>
                    <ActionMenu label={`Actions for ${claim.claim_number}`}>
                      <button type="button" className="action-menu-item" disabled={busy} onClick={() => { setNoteTarget(claim); setNoteText(""); }}>Add internal note</button>
                      {(transitions[claim.status] || []).map((next) => (
                        <button
                          type="button"
                          key={next}
                          className={next === "rejected" ? "action-menu-item danger" : "action-menu-item"}
                          disabled={busy}
                          onClick={() => beginStatusChange(claim, next)}
                        >
                          Move to {next.replaceAll("_", " ")}
                        </button>
                      ))}
                      {!transitions[claim.status]?.length && <button type="button" className="action-menu-item" disabled>No workflow action available</button>}
                    </ActionMenu>
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
          {!claims.items.length && <div className="empty"><strong>No claims found</strong>Register a claim or adjust the current filters.</div>}
        </div>
      </section>

      <SmartDialog
        open={showForm}
        onClose={() => { if (!busy) setShowForm(false); }}
        title="Register claim"
        description="Link the claim to an active policy and capture the incident, priority and claimed amount."
        size="lg"
      >
        <form className="card pad" onSubmit={createClaim}>
          <div className="form-grid">
            <div className="field full"><label>Policy</label><select className="select" value={form.policy_id} onChange={(e) => setForm({ ...form, policy_id: e.target.value })} required><option value="">Select policy</option>{policies.map((policy) => <option key={policy.id} value={policy.id}>{policy.policy_number} · {customerMap.get(policy.customer_id) || "Customer"} · {policy.currency} {Number(policy.sum_insured).toLocaleString()}</option>)}</select></div>
            <div className="field"><label>Claim type</label><input className="input" value={form.claim_type} onChange={(e) => setForm({ ...form, claim_type: e.target.value })} required /></div>
            <div className="field"><label>Priority</label><select className="select" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option></select></div>
            <div className="field"><label>Incident date</label><input className="input" type="date" value={form.incident_date} onChange={(e) => setForm({ ...form, incident_date: e.target.value })} required /></div>
            <div className="field"><label>Claim amount</label><input className="input" type="number" min="0" step="0.01" value={form.claim_amount} onChange={(e) => setForm({ ...form, claim_amount: e.target.value })} required /></div>
            <div className="field full"><label>Description</label><textarea className="textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} minLength={5} required /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setShowForm(false)} disabled={busy}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Register claim"}</button></div>
        </form>
      </SmartDialog>

      <SmartDialog
        open={Boolean(workflowTarget)}
        onClose={() => { if (!busy) setWorkflowTarget(null); }}
        title={workflowTarget ? `Move ${workflowTarget.claim.claim_number} to ${workflowTarget.next.replaceAll("_", " ")}` : "Update claim"}
        description="Confirm the controlled workflow transition and record a note when useful for the audit trail."
        size="sm"
      >
        <form className="card pad" onSubmit={submitStatusChange}>
          <div className="form-grid">
            {workflowTarget?.next === "approved" && (
              <div className="field full"><label>Approved amount</label><input className="input" type="number" min="0" step="0.01" required value={approvedAmount} onChange={(e) => setApprovedAmount(e.target.value)} /></div>
            )}
            <div className="field full"><label>Internal note <span className="muted">(optional)</span></label><textarea className="textarea" value={workflowNote} onChange={(e) => setWorkflowNote(e.target.value)} placeholder="Reason, context or follow-up details…" /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setWorkflowTarget(null)} disabled={busy}>Cancel</button><button className={workflowTarget?.next === "rejected" ? "button danger" : "button"} disabled={busy}>{busy ? "Updating…" : "Confirm transition"}</button></div>
        </form>
      </SmartDialog>

      <SmartDialog
        open={Boolean(noteTarget)}
        onClose={() => { if (!busy) setNoteTarget(null); }}
        title={noteTarget ? `Add note to ${noteTarget.claim_number}` : "Add claim note"}
        description="Internal notes are recorded against the claim timeline for operational continuity."
        size="sm"
      >
        <form className="card pad" onSubmit={submitNote}>
          <div className="field"><label>Internal note</label><textarea className="textarea" value={noteText} onChange={(e) => setNoteText(e.target.value)} minLength={1} required autoFocus placeholder="Add the operational note…" /></div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setNoteTarget(null)} disabled={busy}>Cancel</button><button className="button" disabled={busy || !noteText.trim()}>{busy ? "Saving…" : "Save note"}</button></div>
        </form>
      </SmartDialog>
    </AppShell>
  );
}
