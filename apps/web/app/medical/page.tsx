"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type {
  CustomerList,
  MedicalBenefit,
  MedicalClaim,
  MedicalMember,
  MedicalMemberList,
  MedicalPlan,
} from "@/lib/types";

const emptyMember = { customer_id: "", plan_id: "", start_date: "", end_date: "" };
const emptyPlan = { code: "", name: "", description: "", monthly_premium: "" };
const emptyClaim = {
  member_id: "",
  claim_kind: "medical",
  service_date: "",
  admission_date: "",
  discharge_date: "",
  claim_amount: "",
  provider_name: "",
  description: "",
};

const claimTransitions: Record<string, string[]> = {
  submitted: ["review", "declined"],
  review: ["approved", "declined"],
  approved: ["paid"],
  declined: ["closed"],
  paid: ["closed"],
  closed: [],
};

export default function MedicalPage() {
  const [plans, setPlans] = useState<MedicalPlan[]>([]);
  const [members, setMembers] = useState<MedicalMemberList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [claims, setClaims] = useState<MedicalClaim[]>([]);
  const [search, setSearch] = useState("");
  const [memberStatus, setMemberStatus] = useState("");
  const [showMemberForm, setShowMemberForm] = useState(false);
  const [showPlanForm, setShowPlanForm] = useState(false);
  const [showClaimForm, setShowClaimForm] = useState(false);
  const [memberForm, setMemberForm] = useState(emptyMember);
  const [planForm, setPlanForm] = useState(emptyPlan);
  const [claimForm, setClaimForm] = useState(emptyClaim);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const customerMap = useMemo(
    () => new Map(customers.items.map((item) => [item.id, item.display_name])),
    [customers],
  );
  const planMap = useMemo(() => new Map(plans.map((item) => [item.id, item])), [plans]);
  const memberMap = useMemo(() => new Map(members.items.map((item) => [item.id, item])), [members]);

  const load = useCallback(async () => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (memberStatus) params.set("member_status", memberStatus);
    setError("");
    try {
      const [planData, memberData, customerData, claimData] = await Promise.all([
        apiGet<MedicalPlan[]>("/api/v1/medical/plans?active_only=false"),
        apiGet<MedicalMemberList>(`/api/v1/medical/members?${params}`),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
        apiGet<MedicalClaim[]>("/api/v1/medical/claims"),
      ]);
      setPlans(planData);
      setMembers(memberData);
      setCustomers(customerData);
      setClaims(claimData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load medical aid data.");
    }
  }, [search, memberStatus]);

  useEffect(() => {
    const timer = setTimeout(load, 150);
    return () => clearTimeout(timer);
  }, [load]);

  async function createPlan(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<MedicalPlan>("/api/v1/medical/plans", {
        code: planForm.code,
        name: planForm.name,
        description: planForm.description || null,
        monthly_premium: planForm.monthly_premium || null,
        currency: "LSL",
      });
      setPlanForm(emptyPlan);
      setShowPlanForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create medical plan.");
    } finally {
      setBusy(false);
    }
  }

  async function addBenefit(plan: MedicalPlan) {
    const code = window.prompt(`Benefit code for ${plan.name}:`);
    if (!code?.trim()) return;
    const name = window.prompt("Benefit name:");
    if (!name?.trim()) return;
    const category = window.prompt("Benefit category (for example outpatient, dental, maternity):", "outpatient");
    if (!category?.trim()) return;
    const annualVisits = window.prompt("Annual visit limit (leave blank for no visit limit):", "");
    const annualAmount = window.prompt("Annual monetary limit in LSL (leave blank for no monetary limit):", "");
    const perEvent = window.prompt("Per-event limit in LSL (leave blank for no event limit):", "");
    const requiresAuthorisation = window.confirm("Does this benefit require prior authorisation?");
    setBusy(true);
    setError("");
    try {
      await apiPost<MedicalBenefit>(`/api/v1/medical/plans/${plan.id}/benefits`, {
        code: code.trim(),
        name: name.trim(),
        category: category.trim(),
        annual_visit_limit: annualVisits?.trim() ? Number(annualVisits) : null,
        annual_monetary_limit: annualAmount?.trim() || null,
        per_event_limit: perEvent?.trim() || null,
        requires_authorisation: requiresAuthorisation,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add medical benefit.");
    } finally {
      setBusy(false);
    }
  }

  async function createMember(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<MedicalMember>("/api/v1/medical/members", {
        customer_id: memberForm.customer_id,
        plan_id: memberForm.plan_id,
        start_date: memberForm.start_date,
        end_date: memberForm.end_date || null,
        status: "active",
      });
      setMemberForm(emptyMember);
      setShowMemberForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to enrol medical member.");
    } finally {
      setBusy(false);
    }
  }

  async function addDependant(member: MedicalMember) {
    const firstName = window.prompt(`Dependant first name for ${member.member_number}:`);
    if (!firstName?.trim()) return;
    const lastName = window.prompt("Dependant last name:");
    if (!lastName?.trim()) return;
    const relationship = window.prompt("Relationship (child, spouse, parent, other):", "child");
    if (!relationship?.trim()) return;
    const dateOfBirth = window.prompt("Date of birth (YYYY-MM-DD, optional):", "");
    setBusy(true);
    setError("");
    try {
      await apiPost(`/api/v1/medical/members/${member.id}/dependants`, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        relationship_type: relationship.trim(),
        date_of_birth: dateOfBirth?.trim() || null,
        status: "active",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add dependant.");
    } finally {
      setBusy(false);
    }
  }

  async function recordUse(member: MedicalMember) {
    const plan = planMap.get(member.plan_id);
    if (!plan?.benefits.length) {
      setError("This member plan has no configured benefits yet.");
      return;
    }
    const choices = plan.benefits.map((item) => `${item.code}: ${item.name}`).join("\n");
    const code = window.prompt(`Benefit code to use:\n${choices}`);
    if (!code?.trim()) return;
    const benefit = plan.benefits.find((item) => item.code.toLowerCase() === code.trim().toLowerCase());
    if (!benefit) {
      setError("Benefit code was not found on the member plan.");
      return;
    }
    const amount = window.prompt("Amount used (LSL):", "0");
    if (amount === null) return;
    const units = window.prompt("Visits/units used:", "1");
    if (units === null) return;
    const provider = window.prompt("Provider name (optional):", "");
    setBusy(true);
    setError("");
    try {
      await apiPost("/api/v1/medical/utilisations", {
        member_id: member.id,
        benefit_id: benefit.id,
        service_date: new Date().toISOString().slice(0, 10),
        amount: amount || "0",
        units: Number(units || "1"),
        provider_name: provider?.trim() || null,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to record benefit utilisation.");
    } finally {
      setBusy(false);
    }
  }

  async function createClaim(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<MedicalClaim>("/api/v1/medical/claims", {
        member_id: claimForm.member_id,
        claim_kind: claimForm.claim_kind,
        service_date: claimForm.service_date,
        admission_date: claimForm.admission_date || null,
        discharge_date: claimForm.discharge_date || null,
        claim_amount: claimForm.claim_amount || "0",
        provider_name: claimForm.provider_name || null,
        description: claimForm.description || null,
      });
      setClaimForm(emptyClaim);
      setShowClaimForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create medical claim.");
    } finally {
      setBusy(false);
    }
  }

  async function changeClaimStatus(claim: MedicalClaim, next: string) {
    let approvedAmount: string | undefined;
    if (next === "approved") {
      const value = window.prompt(`Approved amount (claim amount ${claim.claim_amount}):`, claim.claim_amount);
      if (value === null || !value.trim()) return;
      approvedAmount = value.trim();
    }
    setBusy(true);
    setError("");
    try {
      await apiPatch<MedicalClaim>(`/api/v1/medical/claims/${claim.id}/status`, {
        status: next,
        approved_amount: approvedAmount,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update medical claim.");
    } finally {
      setBusy(false);
    }
  }

  const activeMembers = members.items.filter((item) => item.status === "active").length;
  const openClaims = claims.filter((item) => !["paid", "closed", "declined"].includes(item.status)).length;
  const totalBenefits = plans.reduce((sum, plan) => sum + plan.benefits.length, 0);

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Medical Aid</h1>
          <p>Manage plans, benefits, members, dependants, utilisation, authorisations and medical or health-cash claims.</p>
        </div>
        <div className="page-actions">
          <button className="button secondary" onClick={() => setShowPlanForm((value) => !value)}>New plan</button>
          <button className="button secondary" onClick={() => setShowClaimForm((value) => !value)}>Medical claim</button>
          <button className="button" onClick={() => setShowMemberForm((value) => !value)}>Enrol member</button>
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Active members</div><div className="value">{activeMembers}</div><div className="hint">Current enrolled membership</div></div>
        <div className="card metric"><div className="label">Medical plans</div><div className="value">{plans.length}</div><div className="hint">Configured plans</div></div>
        <div className="card metric"><div className="label">Benefits</div><div className="value">{totalBenefits}</div><div className="hint">Rules available across plans</div></div>
        <div className="card metric"><div className="label">Open claims</div><div className="value">{openClaims}</div><div className="hint">Medical and cash-plan workflow</div></div>
      </section>

      {showPlanForm && (
        <form className="card pad" onSubmit={createPlan} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Create medical plan</h2></div>
          <div className="form-grid">
            <div className="field"><label>Code</label><input className="input" value={planForm.code} onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })} required /></div>
            <div className="field"><label>Plan name</label><input className="input" value={planForm.name} onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })} required /></div>
            <div className="field"><label>Monthly premium (LSL)</label><input className="input" type="number" min="0" step="0.01" value={planForm.monthly_premium} onChange={(e) => setPlanForm({ ...planForm, monthly_premium: e.target.value })} /></div>
            <div className="field full"><label>Description</label><textarea className="textarea" value={planForm.description} onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowPlanForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Create plan"}</button></div>
        </form>
      )}

      {showMemberForm && (
        <form className="card pad" onSubmit={createMember} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Enrol medical member</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Customer</label><select className="select" value={memberForm.customer_id} onChange={(e) => setMemberForm({ ...memberForm, customer_id: e.target.value })} required><option value="">Select customer</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.customer_number} · {customer.display_name}</option>)}</select></div>
            <div className="field"><label>Medical plan</label><select className="select" value={memberForm.plan_id} onChange={(e) => setMemberForm({ ...memberForm, plan_id: e.target.value })} required><option value="">Select plan</option>{plans.filter((plan) => plan.is_active).map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select></div>
            <div className="field"><label>Start date</label><input className="input" type="date" value={memberForm.start_date} onChange={(e) => setMemberForm({ ...memberForm, start_date: e.target.value })} required /></div>
            <div className="field"><label>End date (optional)</label><input className="input" type="date" value={memberForm.end_date} onChange={(e) => setMemberForm({ ...memberForm, end_date: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowMemberForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Enrol member"}</button></div>
        </form>
      )}

      {showClaimForm && (
        <form className="card pad" onSubmit={createClaim} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Register medical / health-cash claim</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Member</label><select className="select" value={claimForm.member_id} onChange={(e) => setClaimForm({ ...claimForm, member_id: e.target.value })} required><option value="">Select member</option>{members.items.map((member) => <option key={member.id} value={member.id}>{member.member_number} · {customerMap.get(member.customer_id) || "Customer"}</option>)}</select></div>
            <div className="field"><label>Claim kind</label><select className="select" value={claimForm.claim_kind} onChange={(e) => setClaimForm({ ...claimForm, claim_kind: e.target.value })}><option value="medical">Medical</option><option value="cash_plan">Health cash plan</option></select></div>
            <div className="field"><label>Service date</label><input className="input" type="date" value={claimForm.service_date} onChange={(e) => setClaimForm({ ...claimForm, service_date: e.target.value })} required /></div>
            <div className="field"><label>Admission date</label><input className="input" type="date" value={claimForm.admission_date} onChange={(e) => setClaimForm({ ...claimForm, admission_date: e.target.value })} required={claimForm.claim_kind === "cash_plan"} /></div>
            <div className="field"><label>Discharge date</label><input className="input" type="date" value={claimForm.discharge_date} onChange={(e) => setClaimForm({ ...claimForm, discharge_date: e.target.value })} required={claimForm.claim_kind === "cash_plan"} /></div>
            <div className="field"><label>Claim amount</label><input className="input" type="number" min="0" step="0.01" value={claimForm.claim_amount} onChange={(e) => setClaimForm({ ...claimForm, claim_amount: e.target.value })} required /></div>
            <div className="field"><label>Provider</label><input className="input" value={claimForm.provider_name} onChange={(e) => setClaimForm({ ...claimForm, provider_name: e.target.value })} /></div>
            <div className="field full"><label>Description</label><textarea className="textarea" value={claimForm.description} onChange={(e) => setClaimForm({ ...claimForm, description: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowClaimForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Register claim"}</button></div>
        </form>
      )}

      <section className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><div><h2>Plan & benefit catalogue</h2><p>Benefit limits remain configurable so Guardrisk can apply the exact approved product rules.</p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Plan</th><th>Premium</th><th>Benefits</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{plans.map((plan) => <tr key={plan.id}>
              <td><div className="cell-title">{plan.name}</div><div className="cell-sub">{plan.code} · {plan.description || "No description"}</div></td>
              <td>{plan.monthly_premium ? `${plan.currency} ${Number(plan.monthly_premium).toLocaleString()}` : "Configurable"}</td>
              <td><div className="cell-title">{plan.benefits.length}</div><div className="cell-sub">{plan.benefits.slice(0, 3).map((benefit) => benefit.name).join(" · ") || "No benefits configured"}</div></td>
              <td><span className={`badge ${plan.is_active ? "active" : "cancelled"}`}>{plan.is_active ? "active" : "inactive"}</span></td>
              <td><button className="button secondary small" disabled={busy} onClick={() => addBenefit(plan)}>Add benefit</button></td>
            </tr>)}</tbody>
          </table>
          {!plans.length && <div className="empty"><strong>No medical plans yet</strong>Create the first Guardrisk medical aid plan.</div>}
        </div>
      </section>

      <section className="card" style={{ marginBottom: 20 }}>
        <div className="toolbar">
          <input className="input search" placeholder="Search member number…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 180 }} value={memberStatus} onChange={(e) => setMemberStatus(e.target.value)}><option value="">All member statuses</option>{["active","suspended","expired","cancelled"].map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Member</th><th>Customer</th><th>Plan</th><th>Cover period</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{members.items.map((member) => <tr key={member.id}>
              <td><div className="cell-title">{member.member_number}</div><div className="cell-sub">Created {new Date(member.created_at).toLocaleDateString()}</div></td>
              <td>{customerMap.get(member.customer_id) || member.customer_id.slice(0, 8)}</td>
              <td>{planMap.get(member.plan_id)?.name || member.plan_id.slice(0, 8)}</td>
              <td>{new Date(member.start_date).toLocaleDateString()} → {member.end_date ? new Date(member.end_date).toLocaleDateString() : "Open"}</td>
              <td><span className={`badge ${member.status}`}>{member.status}</span></td>
              <td><div className="actions"><button className="button ghost small" disabled={busy} onClick={() => addDependant(member)}>Add dependant</button><button className="button secondary small" disabled={busy} onClick={() => recordUse(member)}>Record benefit use</button></div></td>
            </tr>)}</tbody>
          </table>
          {!members.items.length && <div className="empty"><strong>No medical members found</strong>Enrol a customer or adjust the filters.</div>}
        </div>
      </section>

      <section className="card">
        <div className="card-header"><div><h2>Medical & health-cash claims</h2><p>Controlled claims workflow separate from general insurance claims.</p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Claim</th><th>Member</th><th>Type / provider</th><th>Amount</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{claims.map((claim) => {
              const member = memberMap.get(claim.member_id);
              return <tr key={claim.id}>
                <td><div className="cell-title">{claim.claim_number}</div><div className="cell-sub">{new Date(claim.service_date).toLocaleDateString()}</div></td>
                <td>{member?.member_number || claim.member_id.slice(0, 8)}</td>
                <td><div className="cell-title">{claim.claim_kind.replaceAll("_", " ")}</div><div className="cell-sub">{claim.provider_name || "No provider"}</div></td>
                <td className="money">LSL {Number(claim.claim_amount).toLocaleString()}</td>
                <td><span className={`badge ${claim.status}`}>{claim.status}</span></td>
                <td><div className="actions">{(claimTransitions[claim.status] || []).map((next) => <button key={next} className={next === "declined" ? "button danger small" : "button secondary small"} disabled={busy} onClick={() => changeClaimStatus(claim, next)}>{next}</button>)}</div></td>
              </tr>;
            })}</tbody>
          </table>
          {!claims.length && <div className="empty"><strong>No medical claims yet</strong>Medical and health-cash claims will appear here.</div>}
        </div>
      </section>
    </AppShell>
  );
}
