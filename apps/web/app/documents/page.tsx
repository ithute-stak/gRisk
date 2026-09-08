"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiDownload, apiGet, apiPatch, apiUpload } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import type { DocumentList, DocumentRecord } from "@/lib/operations-types";
import type { CustomerList } from "@/lib/types";

const categories = [
  "general",
  "identity",
  "policy",
  "quotation",
  "claim",
  "medical",
  "finance",
  "guarantee",
  "risk",
] as const;

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-LS", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function DocumentsPage() {
  const user = currentUser();
  const canWrite = Boolean(
    user?.isSuperuser || user?.roles.some((role) => ["admin", "broker", "claims", "medical", "finance", "risk"].includes(role)),
  );
  const [documents, setDocuments] = useState<DocumentList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [customerId, setCustomerId] = useState("");
  const [category, setCategory] = useState("general");
  const [entityType, setEntityType] = useState("customer");
  const [entityId, setEntityId] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const customerMap = useMemo(
    () => new Map(customers.items.map((customer) => [customer.id, customer.display_name])),
    [customers.items],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (categoryFilter) params.set("category", categoryFilter);
    if (customerFilter) params.set("customer_id", customerFilter);
    try {
      const [documentData, customerData] = await Promise.all([
        apiGet<DocumentList>(`/api/v1/documents?${params.toString()}`),
        apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
      ]);
      setDocuments(documentData);
      setCustomers(customerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load documents.");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, customerFilter, search]);

  useEffect(() => {
    const timer = setTimeout(() => void load(), 120);
    return () => clearTimeout(timer);
  }, [load]);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const form = new FormData();
      form.append("file", file);
      if (customerId) form.append("customer_id", customerId);
      form.append("category", category);
      form.append("entity_type", entityType.trim() || "customer");
      if (entityId.trim()) form.append("entity_id", entityId.trim());
      if (description.trim()) form.append("description", description.trim());
      const created = await apiUpload<DocumentRecord>("/api/v1/documents/upload", form);
      setFile(null);
      setCustomerId("");
      setCategory("general");
      setEntityType("customer");
      setEntityId("");
      setDescription("");
      setShowUpload(false);
      setNotice(`Uploaded ${created.filename}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to upload document.");
    } finally {
      setBusy(false);
    }
  }

  async function download(document: DocumentRecord) {
    setError("");
    try {
      const result = await apiDownload(`/api/v1/documents/${document.id}/download`);
      const url = URL.createObjectURL(result.blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = result.filename || document.filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download document.");
    }
  }

  async function archive(document: DocumentRecord) {
    if (!window.confirm(`Archive ${document.filename}?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiPatch<DocumentRecord>(`/api/v1/documents/${document.id}/archive`, {});
      setNotice(`Archived ${document.filename}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to archive document.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Document Management</h1>
          <p>Securely store and retrieve customer, policy, claim, medical, finance, guarantee and risk documents.</p>
        </div>
        <div className="page-actions">
          <button className="button secondary" onClick={() => void load()} disabled={loading || busy}>{loading ? "Refreshing…" : "Refresh"}</button>
          {canWrite && <button className="button" onClick={() => setShowUpload((value) => !value)}>{showUpload ? "Close upload" : "Upload document"}</button>}
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 14 }}>{error}</div>}
      {notice && <div className="notice" style={{ marginBottom: 14 }}>{notice}</div>}

      <section className="grid metrics" style={{ marginBottom: 18 }}>
        <div className="card metric"><div className="label">Documents</div><div className="value">{documents.total}</div><div className="hint">Active records</div></div>
        <div className="card metric"><div className="label">Customer linked</div><div className="value">{documents.items.filter((item) => item.customer_id).length}</div><div className="hint">Current result set</div></div>
        <div className="card metric"><div className="label">PDF files</div><div className="value">{documents.items.filter((item) => item.content_type === "application/pdf").length}</div><div className="hint">Current result set</div></div>
        <div className="card metric"><div className="label">Stored size</div><div className="value" style={{ fontSize: 24 }}>{formatBytes(documents.items.reduce((sum, item) => sum + item.size_bytes, 0))}</div><div className="hint">Current result set</div></div>
      </section>

      {showUpload && canWrite && (
        <section className="card pad" style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 16 }}><h2>Upload document</h2></div>
          <form onSubmit={upload}>
            <div className="form-grid">
              <div className="field full"><label>File</label><input className="input" type="file" required accept=".pdf,.jpg,.jpeg,.png,.txt,.csv,.doc,.docx,.xls,.xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
              <div className="field"><label>Customer</label><select className="select" value={customerId} onChange={(e) => setCustomerId(e.target.value)}><option value="">Not customer-specific</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.display_name} · {customer.customer_number}</option>)}</select></div>
              <div className="field"><label>Category</label><select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>{categories.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></div>
              <div className="field"><label>Entity type</label><input className="input" value={entityType} onChange={(e) => setEntityType(e.target.value)} placeholder="customer, policy, claim…" /></div>
              <div className="field"><label>Entity ID / reference</label><input className="input" value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="Optional related record ID" /></div>
              <div className="field full"><label>Description</label><textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional document description" /></div>
            </div>
            <div className="form-actions"><button className="button" disabled={busy || !file}>{busy ? "Uploading…" : "Upload"}</button></div>
          </form>
        </section>
      )}

      <section className="card">
        <div className="toolbar">
          <input className="input search" placeholder="Search file name, category, description or reference" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 170 }} value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}><option value="">All categories</option>{categories.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select>
          <select className="select" style={{ width: 240 }} value={customerFilter} onChange={(e) => setCustomerFilter(e.target.value)}><option value="">All customers</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Document</th><th>Customer / link</th><th>Category</th><th>Size</th><th>Uploaded</th><th>Actions</th></tr></thead>
            <tbody>
              {documents.items.map((document) => (
                <tr key={document.id}>
                  <td><div className="cell-title">{document.filename}</div><div className="cell-sub">{document.description || document.content_type}</div></td>
                  <td><div className="cell-title">{document.customer_id ? customerMap.get(document.customer_id) || "Customer" : "Shared / internal"}</div><div className="cell-sub">{humanize(document.entity_type)}{document.entity_id ? ` · ${document.entity_id}` : ""}</div></td>
                  <td><span className="badge active">{humanize(document.category)}</span></td>
                  <td>{formatBytes(document.size_bytes)}</td>
                  <td>{formatDate(document.created_at)}</td>
                  <td><div className="actions"><button className="button secondary small" onClick={() => void download(document)}>Download</button>{canWrite && <button className="button danger small" disabled={busy} onClick={() => void archive(document)}>Archive</button>}</div></td>
                </tr>
              ))}
              {!loading && documents.items.length === 0 && <tr><td colSpan={6}><div className="empty"><strong>No documents found</strong>Upload a document or adjust the current filters.</div></td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
