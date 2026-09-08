"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type {
  CustomerList,
  RiskAssessment,
  RiskAssessmentList,
  RiskDashboard,
  RiskRegisterItem,
} from "@/lib/types";

const assessmentTypes = [
  ["enterprise_risk_management", "Enterprise Risk Management"],
  ["risk_survey", "Risk Survey"],
  ["alternative_risk_transfer", "Alternative Risk Transfer"],
  ["risk_financing", "Risk Financing"],
  ["premium_funding", "Premium Funding"],
  ["general", "General Risk Assessment"],
] as const;

const assessmentTransitions: Record<string, string[]> = {
  draft: ["in_progress", "archived"],
  in_progress: ["review", "archived"],
  review: ["in_progress", "completed", "archived"],
  completed: ["archived"],
  archived: [],
};

const emptyAssessment = {
  customer_id: "",
  assessment_type: "enterprise_risk_management",
  title: "",
  assessment_date: new Date().toISOString().slice(0, 10),
  summary: "",
  recommendations: "",
};

const emptyItem = {
  category: "",
  title: "",
  description: "",
  likelihood: "3",
  impact: "3",
  existing_controls: "",
  treatment_plan: "",
  risk_owner: "",
  due_date: "",
  status: "open",
  residual_likelihood: "",
  residual_impact: "",
};

function typeLabel(value: string): string {
  return assessmentTypes.find(([key]) => key === value)?.[1] ?? value.replaceAll("_", " ");
}

function riskLevel(score: number): string {
  if (score <= 4) return "low";
  if (score <= 9) return "moderate";
  if (score <= 16) return "high";
  return "critical";
}

export default function RiskPage() {
  const [dashboard, setDashboard] = useState<RiskDashboard>({ assessments: 0, open_items: 0, high_or_critical_items: 0, overdue_items: 0 });
  const [assessments, setAssessments] = useState<RiskAssessmentList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [selected, setSelected] = useState<RiskAssessment | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showAssessmentForm, setShowAssessmentForm] = useState(false);
  const [showItemForm, setShowItemForm] = useState(false);
  const [assessmentForm, setAssessmentForm] = useState(emptyAssessment);
  const [itemForm, setItemForm] = useState(emptyItem);
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
    if (statusFilter) params.set("assessment_status", statusFilter);
    if (typeFilter) params.set("assessment_type", typeFilter);
    try {
      const [dashboardData, assessmentData, customerData] = await Promise.all([
        apiGet<RiskDashboard>("/api/v1/risk/dashboard"),
        apiGet<RiskAssessmentList>(`/api/v1/risk/assessments?${params.toString()}`),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
      ]);
      setDashboard(dashboardData);
      setAssessments(assessmentData);
      setCustomers(customerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load risk-management data.");
    }
  }, [search, statusFilter, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(load, 150);
    return () => clearTimeout(timer);
  }, [load]);

  async function createAssessment(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await apiPost<RiskAssessment>("/api/v1/risk/assessments", {
        customer_id: assessmentForm.customer_id,
        assessment_type: assessmentForm.assessment_type,
        title: assessmentForm.title.trim(),
        assessment_date: assessmentForm.assessment_date,
        summary: assessmentForm.summary.trim() || null,
        recommendations: assessmentForm.recommendations.trim() || null,
      });
      setAssessmentForm(emptyAssessment);
      setShowAssessmentForm(false);
      setSelected(created);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create risk assessment.");
    } finally {
      setBusy(false);
    }
  }

  async function openAssessment(item: RiskAssessment) {
    setBusy(true);
    setError("");
    try {
      setSelected(await apiGet<RiskAssessment>(`/api/v1/risk/assessments/${item.id}`));
      setShowItemForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open risk assessment.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSelected(id: string) {
    setSelected(await apiGet<RiskAssessment>(`/api/v1/risk/assessments/${id}`));
  }

  async function changeAssessmentStatus(item: RiskAssessment, next: string) {
    setBusy(true);
    setError("");
    try {
      const updated = await apiPatch<RiskAssessment>(`/api/v1/risk/assessments/${item.id}/status`, { status: next });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change risk-assessment status.");
    } finally {
      setBusy(false);
    }
  }

  async function createRiskItem(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    if ((itemForm.residual_likelihood && !itemForm.residual_impact) || (!itemForm.residual_likelihood && itemForm.residual_impact)) {
      setError("Residual likelihood and residual impact must be entered together.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost<RiskRegisterItem>(`/api/v1/risk/assessments/${selected.id}/items`, {
        category: itemForm.category.trim(),
        title: itemForm.title.trim(),
        description: itemForm.description.trim() || null,
        likelihood: Number(itemForm.likelihood),
        impact: Number(itemForm.impact),
        existing_controls: itemForm.existing_controls.trim() || null,
        treatment_plan: itemForm.treatment_plan.trim() || null,
        risk_owner: itemForm.risk_owner.trim() || null,
        due_date: itemForm.due_date || null,
        status: itemForm.status,
        residual_likelihood: itemForm.residual_likelihood ? Number(itemForm.residual_likelihood) : null,
        residual_impact: itemForm.residual_impact ? Number(itemForm.residual_impact) : null,
      });
      setItemForm(emptyItem);
      setShowItemForm(false);
      await refreshSelected(selected.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add risk-register item.");
    } finally {
      setBusy(false);
    }
  }

  async function manageRiskItem(item: RiskRegisterItem) {
    const statusValue = window.prompt("Status: open, monitoring, mitigated, accepted or closed", item.status);
    if (!statusValue?.trim()) return;
    if (!["open", "monitoring", "mitigated", "accepted", "closed"].includes(statusValue.trim())) {
      setError("Risk item status is not valid.");
      return;
    }
    const owner = window.prompt("Risk owner:", item.risk_owner ?? "");
    if (owner === null) return;
    const treatment = window.prompt("Treatment plan:", item.treatment_plan ?? "");
    if (treatment === null) return;
    const residualLikelihood = window.prompt("Residual likelihood 1-5 (blank to keep inherent score):", item.residual_likelihood?.toString() ?? "");
    if (residualLikelihood === null) return;
    const residualImpact = window.prompt("Residual impact 1-5 (blank to keep inherent score):", item.residual_impact?.toString() ?? "");
    if (residualImpact === null) return;
    if ((residualLikelihood.trim() && !residualImpact.trim()) || (!residualLikelihood.trim() && residualImpact.trim())) {
      setError("Residual likelihood and impact must be supplied together.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPatch<RiskRegisterItem>(`/api/v1/risk/items/${item.id}`, {
        status: statusValue.trim(),
        risk_owner: owner.trim() || null,
        treatment_plan: treatment.trim() || null,
        residual_likelihood: residualLikelihood.trim() ? Number(residualLikelihood) : null,
        residual_impact: residualImpact.trim() ? Number(residualImpact) : null,
      });
      if (selected) await refreshSelected(selected.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update risk item.");
    } finally {
      setBusy(false);
    }
  }

  const previewScore = Number(itemForm.likelihood) * Number(itemForm.impact);

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Risk Management</h1>
          <p>Run enterprise risk assessments, surveys, risk-financing reviews and treatment plans with a controlled risk register.</p>
        </div>
        <div className="page-actions"><button className="button" onClick={() => setShowAssessmentForm((value) => !value)}>New assessment</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Assessments</div><div className="value">{dashboard.assessments}</div><div className="hint">Risk engagements recorded</div></div>
        <div className="card metric"><div className="label">Open risks</div><div className="value">{dashboard.open_items}</div><div className="hint">Items not yet closed</div></div>
        <div className="card metric"><div className="label">High / critical</div><div className="value">{dashboard.high_or_critical_items}</div><div className="hint">Needs management attention</div></div>
        <div className="card metric"><div className="label">Overdue treatments</div><div className="value">{dashboard.overdue_items}</div><div className="hint">Past due and still open</div></div>
      </section>

      {showAssessmentForm && (
        <form className="card pad" onSubmit={createAssessment} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Create risk assessment</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Customer</label><select className="select" value={assessmentForm.customer_id} onChange={(event) => setAssessmentForm({ ...assessmentForm, customer_id: event.target.value })} required><option value="">Select customer</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.customer_number} · {customer.display_name}</option>)}</select></div>
            <div className="field"><label>Assessment type</label><select className="select" value={assessmentForm.assessment_type} onChange={(event) => setAssessmentForm({ ...assessmentForm, assessment_type: event.target.value })}>{assessmentTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <div className="field"><label>Assessment date</label><input className="input" type="date" value={assessmentForm.assessment_date} onChange={(event) => setAssessmentForm({ ...assessmentForm, assessment_date: event.target.value })} required /></div>
            <div className="field full"><label>Title</label><input className="input" value={assessmentForm.title} onChange={(event) => setAssessmentForm({ ...assessmentForm, title: event.target.value })} required /></div>
            <div className="field full"><label>Summary</label><textarea className="textarea" value={assessmentForm.summary} onChange={(event) => setAssessmentForm({ ...assessmentForm, summary: event.target.value })} /></div>
            <div className="field full"><label>Recommendations</label><textarea className="textarea" value={assessmentForm.recommendations} onChange={(event) => setAssessmentForm({ ...assessmentForm, recommendations: event.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowAssessmentForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Create assessment"}</button></div>
        </form>
      )}

      <section className="card" style={{ marginBottom: 18 }}>
        <div className="card-header"><div><h2>Risk assessments</h2><p className="muted">Open an assessment to manage its risk register and treatment workflow.</p></div></div>
        <div className="toolbar">
          <input className="input" placeholder="Search number, title or summary" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select className="select" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="">All assessment types</option>{assessmentTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select className="select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{Object.keys(assessmentTransitions).map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Assessment</th><th>Customer</th><th>Type</th><th>Date</th><th>Status</th><th>Overall level</th><th>Action</th></tr></thead>
            <tbody>
              {assessments.items.map((item) => <tr key={item.id}><td>{item.assessment_number}<br /><strong>{item.title}</strong></td><td>{customerMap.get(item.customer_id) ?? item.customer_id.slice(0, 8)}</td><td>{typeLabel(item.assessment_type)}</td><td>{item.assessment_date}</td><td><strong>{item.status.replaceAll("_", " ")}</strong></td><td><strong>{item.overall_level ?? "not scored"}</strong></td><td><button className="button ghost small" onClick={() => openAssessment(item)}>Open</button></td></tr>)}
              {!assessments.items.length && <tr><td colSpan={7}><div className="empty">No risk assessments match the current filters.</div></td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {selected && (
        <section className="card pad">
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}>
            <div><h2>{selected.assessment_number} · {selected.title}</h2><p className="muted">{typeLabel(selected.assessment_type)} · {customerMap.get(selected.customer_id) ?? "Customer"}</p></div>
            <button className="button ghost small" onClick={() => setSelected(null)}>Close</button>
          </div>
          <div className="grid metrics" style={{ marginBottom: 16 }}>
            <div className="card metric"><div className="label">Status</div><div className="value" style={{ fontSize: 22 }}>{selected.status.replaceAll("_", " ")}</div></div>
            <div className="card metric"><div className="label">Overall level</div><div className="value" style={{ fontSize: 22 }}>{selected.overall_level ?? "Not scored"}</div></div>
            <div className="card metric"><div className="label">Risk items</div><div className="value">{selected.items?.length ?? 0}</div></div>
          </div>
          {selected.summary && <p><strong>Summary:</strong> {selected.summary}</p>}
          {selected.recommendations && <p><strong>Recommendations:</strong> {selected.recommendations}</p>}
          <div className="page-actions" style={{ justifyContent: "flex-start", marginBottom: 18 }}>
            {selected.status !== "completed" && selected.status !== "archived" && <button className="button secondary" onClick={() => setShowItemForm((value) => !value)}>Add risk item</button>}
            {(assessmentTransitions[selected.status] ?? []).map((next) => <button key={next} className="button" disabled={busy} onClick={() => changeAssessmentStatus(selected, next)}>{next.replaceAll("_", " ")}</button>)}
          </div>

          {showItemForm && (
            <form onSubmit={createRiskItem} className="card pad" style={{ marginBottom: 18 }}>
              <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><div><h3>Add risk-register item</h3><p className="muted">Inherent score preview: {previewScore}/25 · {riskLevel(previewScore)}</p></div></div>
              <div className="form-grid">
                <div className="field"><label>Category</label><input className="input" value={itemForm.category} onChange={(event) => setItemForm({ ...itemForm, category: event.target.value })} placeholder="Operational, financial, legal..." required /></div>
                <div className="field"><label>Risk title</label><input className="input" value={itemForm.title} onChange={(event) => setItemForm({ ...itemForm, title: event.target.value })} required /></div>
                <div className="field"><label>Likelihood (1-5)</label><input className="input" type="number" min="1" max="5" value={itemForm.likelihood} onChange={(event) => setItemForm({ ...itemForm, likelihood: event.target.value })} required /></div>
                <div className="field"><label>Impact (1-5)</label><input className="input" type="number" min="1" max="5" value={itemForm.impact} onChange={(event) => setItemForm({ ...itemForm, impact: event.target.value })} required /></div>
                <div className="field"><label>Residual likelihood (optional)</label><input className="input" type="number" min="1" max="5" value={itemForm.residual_likelihood} onChange={(event) => setItemForm({ ...itemForm, residual_likelihood: event.target.value })} /></div>
                <div className="field"><label>Residual impact (optional)</label><input className="input" type="number" min="1" max="5" value={itemForm.residual_impact} onChange={(event) => setItemForm({ ...itemForm, residual_impact: event.target.value })} /></div>
                <div className="field"><label>Risk owner</label><input className="input" value={itemForm.risk_owner} onChange={(event) => setItemForm({ ...itemForm, risk_owner: event.target.value })} /></div>
                <div className="field"><label>Treatment due date</label><input className="input" type="date" value={itemForm.due_date} onChange={(event) => setItemForm({ ...itemForm, due_date: event.target.value })} /></div>
                <div className="field full"><label>Description</label><textarea className="textarea" value={itemForm.description} onChange={(event) => setItemForm({ ...itemForm, description: event.target.value })} /></div>
                <div className="field full"><label>Existing controls</label><textarea className="textarea" value={itemForm.existing_controls} onChange={(event) => setItemForm({ ...itemForm, existing_controls: event.target.value })} /></div>
                <div className="field full"><label>Treatment plan</label><textarea className="textarea" value={itemForm.treatment_plan} onChange={(event) => setItemForm({ ...itemForm, treatment_plan: event.target.value })} /></div>
              </div>
              <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowItemForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Add risk item"}</button></div>
            </form>
          )}

          <div className="card-header" style={{ paddingLeft: 0, paddingRight: 0 }}><div><h3>Risk register</h3><p className="muted">5 × 5 score: 1-4 low, 5-9 moderate, 10-16 high, 17-25 critical.</p></div></div>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Risk</th><th>Owner</th><th>Inherent</th><th>Residual</th><th>Status</th><th>Due</th><th>Action</th></tr></thead>
              <tbody>
                {(selected.items ?? []).map((item) => <tr key={item.id}><td><strong>{item.title}</strong><br /><span className="muted">{item.category}</span></td><td>{item.risk_owner ?? "-"}</td><td><strong>{item.inherent_score}/25 · {item.inherent_level}</strong><br /><span className="muted">L{item.likelihood} × I{item.impact}</span></td><td>{item.residual_score !== null ? <><strong>{item.residual_score}/25 · {item.residual_level}</strong><br /><span className="muted">L{item.residual_likelihood} × I{item.residual_impact}</span></> : "Not assessed"}</td><td>{item.status}</td><td>{item.due_date ?? "-"}</td><td><button className="button ghost small" disabled={busy || selected.status === "archived"} onClick={() => manageRiskItem(item)}>Manage</button></td></tr>)}
                {!selected.items?.length && <tr><td colSpan={7}><div className="empty">No risk items have been added yet.</div></td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </AppShell>
  );
}
