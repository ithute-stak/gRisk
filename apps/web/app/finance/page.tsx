"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { CustomerList, MedicalMemberList, Policy } from "@/lib/types";
import type { FinanceDashboard, Invoice, InvoiceList, Payment } from "@/lib/phase7-types";

const invoiceTypes = [
  ["premium", "Insurance premium"],
  ["medical", "Medical aid"],
  ["service_fee", "Service fee"],
  ["guarantee_fee", "Guarantee fee"],
  ["other", "Other"],
] as const;

const paymentMethods = [
  ["bank_transfer", "Bank transfer"],
  ["cash", "Cash"],
  ["card", "Card"],
  ["mobile_money", "Mobile money"],
  ["cheque", "Cheque"],
  ["other", "Other"],
] as const;

const today = () => new Date().toISOString().slice(0, 10);
const inThirtyDays = () => {
  const date = new Date();
  date.setDate(date.getDate() + 30);
  return date.toISOString().slice(0, 10);
};

const emptyInvoice = {
  customer_id: "",
  policy_id: "",
  medical_member_id: "",
  invoice_type: "premium",
  description: "",
  amount_due: "",
  issue_date: today(),
  due_date: inThirtyDays(),
  notes: "",
};

const emptyPayment = {
  amount: "",
  payment_date: today(),
  payment_method: "bank_transfer",
  reference: "",
  notes: "",
};

const money = new Intl.NumberFormat("en-LS", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function effectiveStatus(invoice: Invoice): string {
  if (["issued", "partially_paid"].includes(invoice.status) && invoice.due_date < today()) return "overdue";
  return invoice.status;
}

export default function FinancePage() {
  const [dashboard, setDashboard] = useState<FinanceDashboard>({ invoices: 0, outstanding_invoices: 0, overdue_invoices: 0, currency: "LSL", total_invoiced: "0", total_received: "0", outstanding_balance: "0" });
  const [invoices, setInvoices] = useState<InvoiceList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [members, setMembers] = useState<MedicalMemberList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [showInvoiceForm, setShowInvoiceForm] = useState(false);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [invoiceForm, setInvoiceForm] = useState(emptyInvoice);
  const [paymentForm, setPaymentForm] = useState(emptyPayment);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const customerMap = useMemo(
    () => new Map(customers.items.map((customer) => [customer.id, customer.display_name])),
    [customers],
  );

  const selectedCustomerPolicies = policies.filter((policy) => policy.customer_id === invoiceForm.customer_id);
  const selectedCustomerMembers = members.items.filter((member) => member.customer_id === invoiceForm.customer_id);

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (statusFilter) params.set("invoice_status", statusFilter);
    if (typeFilter) params.set("invoice_type", typeFilter);
    try {
      const [dashboardData, invoiceData, customerData, policyData, memberData] = await Promise.all([
        apiGet<FinanceDashboard>("/api/v1/finance/dashboard"),
        apiGet<InvoiceList>(`/api/v1/finance/invoices?${params.toString()}`),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
        apiGet<Policy[]>("/api/v1/insurance/policies"),
        apiGet<MedicalMemberList>("/api/v1/medical/members?page=1&page_size=100"),
      ]);
      setDashboard(dashboardData);
      setInvoices(invoiceData);
      setCustomers(customerData);
      setPolicies(policyData);
      setMembers(memberData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load finance workspace.");
    }
  }, [search, statusFilter, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(load, 150);
    return () => clearTimeout(timer);
  }, [load]);

  async function createInvoice(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await apiPost<Invoice>("/api/v1/finance/invoices", {
        customer_id: invoiceForm.customer_id,
        policy_id: invoiceForm.policy_id || null,
        medical_member_id: invoiceForm.medical_member_id || null,
        invoice_type: invoiceForm.invoice_type,
        description: invoiceForm.description.trim(),
        currency: "LSL",
        amount_due: invoiceForm.amount_due,
        issue_date: invoiceForm.issue_date,
        due_date: invoiceForm.due_date,
        notes: invoiceForm.notes.trim() || null,
      });
      setInvoiceForm(emptyInvoice);
      setShowInvoiceForm(false);
      setSelected(created);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create invoice.");
    } finally {
      setBusy(false);
    }
  }

  async function openInvoice(invoice: Invoice) {
    setBusy(true);
    setError("");
    try {
      setSelected(await apiGet<Invoice>(`/api/v1/finance/invoices/${invoice.id}`));
      setShowPaymentForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open invoice.");
    } finally {
      setBusy(false);
    }
  }

  async function setInvoiceStatus(invoice: Invoice, next: "issued" | "cancelled") {
    setBusy(true);
    setError("");
    try {
      const updated = await apiPatch<Invoice>(`/api/v1/finance/invoices/${invoice.id}/status`, { status: next });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update invoice status.");
    } finally {
      setBusy(false);
    }
  }

  async function recordPayment(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await apiPost<Payment>("/api/v1/finance/payments", {
        invoice_id: selected.id,
        amount: paymentForm.amount,
        payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        reference: paymentForm.reference.trim() || null,
        notes: paymentForm.notes.trim() || null,
      });
      setPaymentForm(emptyPayment);
      setShowPaymentForm(false);
      setSelected(await apiGet<Invoice>(`/api/v1/finance/invoices/${selected.id}`));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to record payment.");
    } finally {
      setBusy(false);
    }
  }

  const selectedOutstanding = selected ? Math.max(0, Number(selected.amount_due) - Number(selected.amount_paid)) : 0;

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Finance</h1>
          <p>Control invoices, premium receivables, customer balances and payment allocation in one finance register.</p>
        </div>
        <div className="page-actions"><button className="button" onClick={() => setShowInvoiceForm((value) => !value)}>New invoice</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Invoices</div><div className="value">{dashboard.invoices}</div><div className="hint">Non-cancelled invoices</div></div>
        <div className="card metric"><div className="label">Total invoiced</div><div className="value">M {money.format(Number(dashboard.total_invoiced))}</div><div className="hint">Gross billing</div></div>
        <div className="card metric"><div className="label">Received</div><div className="value">M {money.format(Number(dashboard.total_received))}</div><div className="hint">Recorded payments</div></div>
        <div className="card metric"><div className="label">Outstanding</div><div className="value">M {money.format(Number(dashboard.outstanding_balance))}</div><div className="hint">Open receivables</div></div>
        <div className="card metric"><div className="label">Overdue</div><div className="value">{dashboard.overdue_invoices}</div><div className="hint">Past due and unpaid</div></div>
      </section>

      {showInvoiceForm && (
        <form className="card pad" onSubmit={createInvoice} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Create invoice</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Customer</label><select className="select" required value={invoiceForm.customer_id} onChange={(event) => setInvoiceForm({ ...invoiceForm, customer_id: event.target.value, policy_id: "", medical_member_id: "" })}><option value="">Select customer</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.customer_number} · {customer.display_name}</option>)}</select></div>
            <div className="field"><label>Invoice type</label><select className="select" value={invoiceForm.invoice_type} onChange={(event) => setInvoiceForm({ ...invoiceForm, invoice_type: event.target.value })}>{invoiceTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <div className="field"><label>Amount (LSL)</label><input className="input" type="number" min="0.01" step="0.01" required value={invoiceForm.amount_due} onChange={(event) => setInvoiceForm({ ...invoiceForm, amount_due: event.target.value })} /></div>
            <div className="field"><label>Policy (optional)</label><select className="select" value={invoiceForm.policy_id} onChange={(event) => setInvoiceForm({ ...invoiceForm, policy_id: event.target.value })}><option value="">No policy link</option>{selectedCustomerPolicies.map((policy) => <option key={policy.id} value={policy.id}>{policy.policy_number}</option>)}</select></div>
            <div className="field"><label>Medical member (optional)</label><select className="select" value={invoiceForm.medical_member_id} onChange={(event) => setInvoiceForm({ ...invoiceForm, medical_member_id: event.target.value })}><option value="">No medical member link</option>{selectedCustomerMembers.map((member) => <option key={member.id} value={member.id}>{member.member_number}</option>)}</select></div>
            <div className="field"><label>Issue date</label><input className="input" type="date" required value={invoiceForm.issue_date} onChange={(event) => setInvoiceForm({ ...invoiceForm, issue_date: event.target.value })} /></div>
            <div className="field"><label>Due date</label><input className="input" type="date" required value={invoiceForm.due_date} onChange={(event) => setInvoiceForm({ ...invoiceForm, due_date: event.target.value })} /></div>
            <div className="field full"><label>Description</label><input className="input" required value={invoiceForm.description} onChange={(event) => setInvoiceForm({ ...invoiceForm, description: event.target.value })} placeholder="What is being billed?" /></div>
            <div className="field full"><label>Notes</label><textarea className="textarea" value={invoiceForm.notes} onChange={(event) => setInvoiceForm({ ...invoiceForm, notes: event.target.value })} /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowInvoiceForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Create invoice"}</button></div>
        </form>
      )}

      <section className="card" style={{ marginBottom: 18 }}>
        <div className="card-header"><div><h2>Invoice register</h2><p className="muted">Draft, issue, collect and reconcile customer invoices.</p></div></div>
        <div className="toolbar">
          <input className="input" placeholder="Search invoice or description" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select className="select" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="">All types</option>{invoiceTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select className="select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{["draft", "issued", "partially_paid", "paid", "cancelled"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table className="table"><thead><tr><th>Invoice</th><th>Customer</th><th>Type</th><th>Due</th><th>Amount</th><th>Paid</th><th>Status</th><th>Action</th></tr></thead><tbody>
            {invoices.items.map((invoice) => <tr key={invoice.id}><td><strong>{invoice.invoice_number}</strong><br /><span className="muted">{invoice.description}</span></td><td>{customerMap.get(invoice.customer_id) ?? invoice.customer_id.slice(0, 8)}</td><td>{invoice.invoice_type.replaceAll("_", " ")}</td><td>{invoice.due_date}</td><td>{invoice.currency} {money.format(Number(invoice.amount_due))}</td><td>{invoice.currency} {money.format(Number(invoice.amount_paid))}</td><td><strong>{effectiveStatus(invoice).replaceAll("_", " ")}</strong></td><td><button className="button ghost small" onClick={() => openInvoice(invoice)}>Open</button></td></tr>)}
            {!invoices.items.length && <tr><td colSpan={8}><div className="empty">No invoices match the current filters.</div></td></tr>}
          </tbody></table>
        </div>
      </section>

      {selected && (
        <section className="card pad">
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><div><h2>{selected.invoice_number}</h2><p className="muted">{customerMap.get(selected.customer_id) ?? "Customer"} · {selected.description}</p></div><button className="button ghost small" onClick={() => setSelected(null)}>Close</button></div>
          <div className="grid metrics" style={{ marginBottom: 18 }}>
            <div className="card metric"><div className="label">Amount due</div><div className="value" style={{ fontSize: 22 }}>M {money.format(Number(selected.amount_due))}</div></div>
            <div className="card metric"><div className="label">Amount paid</div><div className="value" style={{ fontSize: 22 }}>M {money.format(Number(selected.amount_paid))}</div></div>
            <div className="card metric"><div className="label">Outstanding</div><div className="value" style={{ fontSize: 22 }}>M {money.format(selectedOutstanding)}</div></div>
            <div className="card metric"><div className="label">Status</div><div className="value" style={{ fontSize: 22 }}>{effectiveStatus(selected).replaceAll("_", " ")}</div></div>
          </div>
          <div className="page-actions" style={{ justifyContent: "flex-start", marginBottom: 18 }}>
            {selected.status === "draft" && <button className="button" disabled={busy} onClick={() => setInvoiceStatus(selected, "issued")}>Issue invoice</button>}
            {["draft", "issued"].includes(selected.status) && Number(selected.amount_paid) === 0 && <button className="button secondary" disabled={busy} onClick={() => setInvoiceStatus(selected, "cancelled")}>Cancel invoice</button>}
            {["issued", "partially_paid"].includes(selected.status) && selectedOutstanding > 0 && <button className="button" onClick={() => { setPaymentForm({ ...emptyPayment, amount: selectedOutstanding.toFixed(2) }); setShowPaymentForm((value) => !value); }}>Record payment</button>}
          </div>

          {showPaymentForm && (
            <form className="card pad" onSubmit={recordPayment} style={{ marginBottom: 18 }}>
              <h3 style={{ marginTop: 0 }}>Record payment</h3>
              <div className="form-grid">
                <div className="field"><label>Amount</label><input className="input" type="number" min="0.01" max={selectedOutstanding} step="0.01" required value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} /></div>
                <div className="field"><label>Payment date</label><input className="input" type="date" required value={paymentForm.payment_date} onChange={(event) => setPaymentForm({ ...paymentForm, payment_date: event.target.value })} /></div>
                <div className="field"><label>Method</label><select className="select" value={paymentForm.payment_method} onChange={(event) => setPaymentForm({ ...paymentForm, payment_method: event.target.value })}>{paymentMethods.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
                <div className="field"><label>Reference</label><input className="input" value={paymentForm.reference} onChange={(event) => setPaymentForm({ ...paymentForm, reference: event.target.value })} /></div>
                <div className="field full"><label>Notes</label><textarea className="textarea" value={paymentForm.notes} onChange={(event) => setPaymentForm({ ...paymentForm, notes: event.target.value })} /></div>
              </div>
              <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowPaymentForm(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving..." : "Record payment"}</button></div>
            </form>
          )}

          <div className="card-header" style={{ paddingLeft: 0, paddingRight: 0 }}><h3>Payment history</h3></div>
          <div className="table-wrap"><table className="table"><thead><tr><th>Payment</th><th>Date</th><th>Method</th><th>Reference</th><th>Amount</th></tr></thead><tbody>
            {(selected.payments ?? []).map((payment) => <tr key={payment.id}><td>{payment.payment_number}</td><td>{payment.payment_date}</td><td>{payment.payment_method.replaceAll("_", " ")}</td><td>{payment.reference ?? "-"}</td><td>{payment.currency} {money.format(Number(payment.amount))}</td></tr>)}
            {!selected.payments?.length && <tr><td colSpan={5}>No payments recorded.</td></tr>}
          </tbody></table></div>
        </section>
      )}
    </AppShell>
  );
}
