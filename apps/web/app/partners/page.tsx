"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import type { Partner, PartnerList } from "@/lib/operations-types";

const partnerTypes = [
  "insurer",
  "bank",
  "medical_provider",
  "payment_provider",
  "sms_provider",
  "email_provider",
  "other",
] as const;
const integrationStatuses = ["not_configured", "sandbox", "active", "paused", "error"] as const;

const emptyForm = {
  partner_type: "insurer",
  name: "",
  email: "",
  phone: "",
  website: "",
  external_reference: "",
  integration_status: "not_configured",
  notes: "",
  is_active: true,
};

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function PartnersPage() {
  const user = currentUser();
  const canWrite = Boolean(user?.isSuperuser || user?.roles.some((role) => ["admin", "broker", "risk"].includes(role)));
  const [partners, setPartners] = useState<PartnerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(emptyForm);
  const [editForm, setEditForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selected = useMemo(() => partners.items.find((partner) => partner.id === selectedId) ?? null, [partners.items, selectedId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (typeFilter) params.set("partner_type", typeFilter);
    if (statusFilter) params.set("integration_status", statusFilter);
    try {
      const data = await apiGet<PartnerList>(`/api/v1/partners?${params.toString()}`);
      setPartners(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load partners.");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(() => void load(), 120);
    return () => clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!selected) return;
    setEditForm({
      partner_type: selected.partner_type,
      name: selected.name,
      email: selected.email || "",
      phone: selected.phone || "",
      website: selected.website || "",
      external_reference: selected.external_reference || "",
      integration_status: selected.integration_status,
      notes: selected.notes || "",
      is_active: selected.is_active,
    });
  }, [selected]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await apiPost<Partner>("/api/v1/partners", {
        ...createForm,
        email: createForm.email || null,
        phone: createForm.phone || null,
        website: createForm.website || null,
        external_reference: createForm.external_reference || null,
        notes: createForm.notes || null,
      });
      setCreateForm(emptyForm);
      setShowCreate(false);
      setNotice(`Created partner ${created.name}.`);
      await load();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create partner.");
    } finally {
      setBusy(false);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await apiPatch<Partner>(`/api/v1/partners/${selected.id}`, {
        ...editForm,
        email: editForm.email || null,
        phone: editForm.phone || null,
        website: editForm.website || null,
        external_reference: editForm.external_reference || null,
        notes: editForm.notes || null,
      });
      setNotice(`Updated ${updated.name}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update partner.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Strategic Partners</h1>
          <p>Manage insurers, banks, medical providers and delivery partners without hard-coding provider-specific integrations.</p>
        </div>
        <div className="page-actions">
          <button className="button secondary" onClick={() => void load()} disabled={loading || busy}>{loading ? "Refreshing…" : "Refresh"}</button>
          {canWrite && <button className="button" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Close form" : "New partner"}</button>}
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 14 }}>{error}</div>}
      {notice && <div className="notice" style={{ marginBottom: 14 }}>{notice}</div>}

      <section className="grid metrics" style={{ marginBottom: 18 }}>
        <div className="card metric"><div className="label">Partners</div><div className="value">{partners.total}</div><div className="hint">Current partner register</div></div>
        <div className="card metric"><div className="label">Active</div><div className="value">{partners.items.filter((partner) => partner.is_active).length}</div><div className="hint">Current result set</div></div>
        <div className="card metric"><div className="label">Integrated</div><div className="value">{partners.items.filter((partner) => partner.integration_status === "active").length}</div><div className="hint">Marked active integrations</div></div>
        <div className="card metric"><div className="label">Sandbox</div><div className="value">{partners.items.filter((partner) => partner.integration_status === "sandbox").length}</div><div className="hint">Integration testing</div></div>
      </section>

      {showCreate && canWrite && (
        <section className="card pad" style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 16 }}><h2>Create strategic partner</h2></div>
          <PartnerForm form={createForm} setForm={setCreateForm} busy={busy} submitLabel="Create partner" onSubmit={create} />
        </section>
      )}

      <div className="grid two">
        <section className="card">
          <div className="toolbar">
            <input className="input search" placeholder="Search partner name, number, email or reference" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="select" style={{ width: 170 }} value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="">All types</option>{partnerTypes.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select>
            <select className="select" style={{ width: 160 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">All integration states</option>{integrationStatuses.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Partner</th><th>Type</th><th>Integration</th><th>Status</th></tr></thead>
              <tbody>
                {partners.items.map((partner) => (
                  <tr key={partner.id} onClick={() => setSelectedId(partner.id)} style={{ cursor: "pointer", background: selectedId === partner.id ? "#f0f8f6" : undefined }}>
                    <td><div className="cell-title">{partner.name}</div><div className="cell-sub">{partner.partner_number}{partner.email ? ` · ${partner.email}` : ""}</div></td>
                    <td>{humanize(partner.partner_type)}</td>
                    <td><span className={`badge ${partner.integration_status === "active" ? "active" : partner.integration_status === "error" ? "rejected" : "review"}`}>{humanize(partner.integration_status)}</span></td>
                    <td><span className={`badge ${partner.is_active ? "active" : "cancelled"}`}>{partner.is_active ? "active" : "inactive"}</span></td>
                  </tr>
                ))}
                {!loading && partners.items.length === 0 && <tr><td colSpan={4}><div className="empty"><strong>No partners found</strong>Create the first partner or change the filters.</div></td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card pad">
          {!selected ? (
            <div className="empty"><strong>Select a partner</strong>Choose a partner to view or manage its integration profile.</div>
          ) : (
            <>
              <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 16 }}>
                <div><h2>{selected.name}</h2><div className="cell-sub">{selected.partner_number}</div></div>
                <span className={`badge ${selected.is_active ? "active" : "cancelled"}`}>{selected.is_active ? "active" : "inactive"}</span>
              </div>
              {canWrite ? (
                <PartnerForm form={editForm} setForm={setEditForm} busy={busy} submitLabel="Save partner" onSubmit={save} />
              ) : (
                <div style={{ display: "grid", gap: 12 }}>
                  <div><strong>Type</strong><div className="cell-sub">{humanize(selected.partner_type)}</div></div>
                  <div><strong>Integration status</strong><div className="cell-sub">{humanize(selected.integration_status)}</div></div>
                  <div><strong>Contact</strong><div className="cell-sub">{selected.email || selected.phone || "Not recorded"}</div></div>
                  <div><strong>External reference</strong><div className="cell-sub">{selected.external_reference || "Not recorded"}</div></div>
                  <div><strong>Notes</strong><div className="cell-sub">{selected.notes || "No notes"}</div></div>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function PartnerForm({
  form,
  setForm,
  busy,
  submitLabel,
  onSubmit,
}: {
  form: typeof emptyForm;
  setForm: (form: typeof emptyForm) => void;
  busy: boolean;
  submitLabel: string;
  onSubmit: (event: FormEvent) => void | Promise<void>;
}) {
  return (
    <form onSubmit={onSubmit}>
      <div className="form-grid">
        <div className="field"><label>Name</label><input className="input" required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
        <div className="field"><label>Partner type</label><select className="select" value={form.partner_type} onChange={(e) => setForm({ ...form, partner_type: e.target.value })}>{partnerTypes.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></div>
        <div className="field"><label>Email</label><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
        <div className="field"><label>Phone</label><input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
        <div className="field"><label>Website</label><input className="input" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://…" /></div>
        <div className="field"><label>External reference</label><input className="input" value={form.external_reference} onChange={(e) => setForm({ ...form, external_reference: e.target.value })} /></div>
        <div className="field"><label>Integration status</label><select className="select" value={form.integration_status} onChange={(e) => setForm({ ...form, integration_status: e.target.value })}>{integrationStatuses.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></div>
        <div className="field"><label style={{ display: "inline-flex", alignItems: "center", gap: 8, marginTop: 26 }}><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active partner</label></div>
        <div className="field full"><label>Notes</label><textarea className="textarea" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      </div>
      <div className="form-actions"><button className="button" disabled={busy || form.name.trim().length < 2}>{busy ? "Saving…" : submitLabel}</button></div>
    </form>
  );
}
