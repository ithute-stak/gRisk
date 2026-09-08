"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { ActionMenu, SmartDialog } from "@/components/SmartUi";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { CustomerList, InsuranceProduct, Policy, Quote, QuoteList } from "@/lib/types";

const emptyForm = {
  customer_id: "",
  product_id: "",
  currency: "LSL",
  sum_insured: "",
  premium: "",
  third_party_limit: "",
  start_date: "",
  end_date: "",
  notes: "",
};

const nextStatus: Record<string, string[]> = {
  draft: ["review"],
  review: ["submitted", "declined"],
  submitted: ["accepted", "declined"],
};

export default function QuotationsPage() {
  const [quotes, setQuotes] = useState<QuoteList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [products, setProducts] = useState<InsuranceProduct[]>([]);
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [convertQuote, setConvertQuote] = useState<Quote | null>(null);
  const [convertDates, setConvertDates] = useState({ start_date: "", end_date: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const customerMap = useMemo(() => new Map(customers.items.map((item) => [item.id, item.display_name])), [customers]);
  const productMap = useMemo(() => new Map(products.map((item) => [item.id, item.name])), [products]);

  const load = useCallback(async () => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (status) params.set("quote_status", status);
    setError("");
    try {
      const [quoteData, productData, customerData] = await Promise.all([
        apiGet<QuoteList>(`/api/v1/insurance/quotes?${params}`),
        apiGet<InsuranceProduct[]>("/api/v1/insurance/products"),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
      ]);
      setQuotes(quoteData);
      setProducts(productData);
      setCustomers(customerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load quotations.");
    }
  }, [search, status]);

  useEffect(() => { const timer = setTimeout(load, 180); return () => clearTimeout(timer); }, [load]);

  async function createQuote(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<Quote>("/api/v1/insurance/quotes", {
        customer_id: form.customer_id,
        product_id: form.product_id,
        currency: form.currency,
        sum_insured: form.sum_insured || "0",
        premium: form.premium || "0",
        third_party_limit: form.third_party_limit || null,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        notes: form.notes || null,
        items: [],
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create quotation.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(quote: Quote, newStatus: string) {
    setBusy(true);
    setError("");
    try {
      await apiPatch<Quote>(`/api/v1/insurance/quotes/${quote.id}/status`, { status: newStatus });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update quotation.");
    } finally {
      setBusy(false);
    }
  }

  async function issuePolicy(event: FormEvent) {
    event.preventDefault();
    if (!convertQuote) return;
    setBusy(true);
    setError("");
    try {
      await apiPost<Policy>(`/api/v1/insurance/quotes/${convertQuote.id}/convert-to-policy`, convertDates);
      setConvertQuote(null);
      setConvertDates({ start_date: "", end_date: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to issue policy.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div><h1>Quotations</h1><p>Create insurance quotations and move them through controlled review, submission and acceptance before policy issuance.</p></div>
        <div className="page-actions"><button className="button" onClick={() => setShowForm(true)}>New quotation</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="card">
        <div className="toolbar">
          <input className="input search" placeholder="Search quotation number…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 180 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{["draft","review","submitted","accepted","declined","expired","converted"].map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Quotation</th><th>Customer</th><th>Product</th><th>Sum insured</th><th>Premium</th><th>Status</th><th aria-label="Actions" /></tr></thead>
            <tbody>{quotes.items.map((quote) => (
              <tr key={quote.id}>
                <td><div className="cell-title">{quote.quote_number}</div><div className="cell-sub">{new Date(quote.created_at).toLocaleDateString()}</div></td>
                <td>{customerMap.get(quote.customer_id) || quote.customer_id.slice(0, 8)}</td>
                <td>{productMap.get(quote.product_id) || quote.product_id.slice(0, 8)}</td>
                <td className="money">{quote.currency} {Number(quote.sum_insured).toLocaleString()}</td>
                <td className="money">{quote.currency} {Number(quote.premium).toLocaleString()}</td>
                <td><span className={`badge ${quote.status}`}>{quote.status}</span></td>
                <td>
                  <ActionMenu label={`Actions for ${quote.quote_number}`}>
                    {(nextStatus[quote.status] || []).map((next) => (
                      <button
                        type="button"
                        key={next}
                        className={next === "declined" ? "action-menu-item danger" : "action-menu-item"}
                        disabled={busy}
                        onClick={() => changeStatus(quote, next)}
                      >
                        Move to {next}
                      </button>
                    ))}
                    {quote.status === "accepted" && (
                      <button
                        type="button"
                        className="action-menu-item"
                        disabled={busy}
                        onClick={() => {
                          setConvertQuote(quote);
                          setConvertDates({ start_date: quote.start_date || "", end_date: quote.end_date || "" });
                        }}
                      >
                        Issue policy <span aria-hidden="true">→</span>
                      </button>
                    )}
                    {!nextStatus[quote.status]?.length && quote.status !== "accepted" && <button type="button" className="action-menu-item" disabled>No workflow action available</button>}
                  </ActionMenu>
                </td>
              </tr>
            ))}</tbody>
          </table>
          {!quotes.items.length && <div className="empty"><strong>No quotations found</strong>Create a quotation or adjust your filters.</div>}
        </div>
      </section>

      <SmartDialog
        open={showForm}
        onClose={() => { if (!busy) setShowForm(false); }}
        title="Create quotation"
        description="Capture the insured value, premium and cover period, then move the quotation through the controlled review workflow."
        size="lg"
      >
        <form className="card pad" onSubmit={createQuote}>
          <div className="form-grid">
            <div className="field"><label>Customer</label><select className="select" value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} required><option value="">Select customer</option>{customers.items.map((item) => <option key={item.id} value={item.id}>{item.display_name} · {item.customer_number}</option>)}</select></div>
            <div className="field"><label>Insurance product</label><select className="select" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required><option value="">Select product</option>{products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
            <div className="field"><label>Sum insured</label><input className="input" type="number" min="0" step="0.01" value={form.sum_insured} onChange={(e) => setForm({ ...form, sum_insured: e.target.value })} required /></div>
            <div className="field"><label>Premium</label><input className="input" type="number" min="0" step="0.01" value={form.premium} onChange={(e) => setForm({ ...form, premium: e.target.value })} required /></div>
            <div className="field"><label>Third-party limit</label><input className="input" type="number" min="0" step="0.01" value={form.third_party_limit} onChange={(e) => setForm({ ...form, third_party_limit: e.target.value })} /></div>
            <div className="field"><label>Currency</label><input className="input" maxLength={3} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} required /></div>
            <div className="field"><label>Cover start</label><input className="input" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
            <div className="field"><label>Cover end</label><input className="input" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
            <div className="field full"><label>Notes</label><textarea className="textarea" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setShowForm(false)} disabled={busy}>Cancel</button><button className="button" disabled={busy}>{busy ? "Saving…" : "Create quotation"}</button></div>
        </form>
      </SmartDialog>

      <SmartDialog
        open={Boolean(convertQuote)}
        onClose={() => { if (!busy) setConvertQuote(null); }}
        title={convertQuote ? `Issue policy from ${convertQuote.quote_number}` : "Issue policy"}
        description="Confirm the final policy period. Policy issuance is only available after the quotation has been accepted."
        size="sm"
      >
        <form className="card pad" onSubmit={issuePolicy}>
          <div className="form-grid">
            <div className="field"><label>Policy start date</label><input className="input" type="date" required value={convertDates.start_date} onChange={(e) => setConvertDates({ ...convertDates, start_date: e.target.value })} /></div>
            <div className="field"><label>Policy end date</label><input className="input" type="date" required value={convertDates.end_date} onChange={(e) => setConvertDates({ ...convertDates, end_date: e.target.value })} /></div>
          </div>
          <div className="form-actions"><button className="button secondary" type="button" onClick={() => setConvertQuote(null)} disabled={busy}>Cancel</button><button className="button" disabled={busy}>{busy ? "Issuing…" : "Issue policy"}</button></div>
        </form>
      </SmartDialog>
    </AppShell>
  );
}
