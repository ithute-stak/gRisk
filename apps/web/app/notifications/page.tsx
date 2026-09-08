"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import type { CustomerList } from "@/lib/types";
import type { NotificationItem, NotificationList, PortalUser } from "@/lib/phase7-types";

const categories = ["general", "finance", "policy", "claim", "medical", "guarantee", "risk", "portal"];

const emptyForm = {
  user_id: "",
  customer_id: "",
  category: "general",
  title: "",
  message: "",
  action_url: "",
};

export default function NotificationsPage() {
  const user = currentUser();
  const [data, setData] = useState<NotificationList>({ items: [], total: 0, unread: 0 });
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showSend, setShowSend] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const customerMap = useMemo(
    () => new Map(customers.items.map((item) => [item.id, item.display_name])),
    [customers],
  );

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams();
    if (statusFilter) params.set("notification_status", statusFilter);
    if (categoryFilter) params.set("category", categoryFilter);
    try {
      const notifications = await apiGet<NotificationList>(`/api/v1/notifications${params.size ? `?${params.toString()}` : ""}`);
      setData(notifications);
      if (user?.isSuperuser) {
        const [userData, customerData] = await Promise.all([
          apiGet<PortalUser[]>("/api/v1/portal/users"),
          apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
        ]);
        setUsers(userData);
        setCustomers(customerData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load notifications.");
    }
  }, [categoryFilter, statusFilter, user?.isSuperuser]);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead(item: NotificationItem) {
    setBusy(true);
    setError("");
    try {
      await apiPatch<NotificationItem>(`/api/v1/notifications/${item.id}/read`, {});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to mark notification as read.");
    } finally {
      setBusy(false);
    }
  }

  async function archive(item: NotificationItem) {
    setBusy(true);
    setError("");
    try {
      await apiPatch<NotificationItem>(`/api/v1/notifications/${item.id}/archive`, {});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to archive notification.");
    } finally {
      setBusy(false);
    }
  }

  async function readAll() {
    setBusy(true);
    setError("");
    try {
      setData(await apiPatch<NotificationList>("/api/v1/notifications/read-all", {}));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to mark notifications as read.");
    } finally {
      setBusy(false);
    }
  }

  async function sendNotification(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiPost<NotificationItem>("/api/v1/notifications", {
        user_id: form.user_id,
        customer_id: form.customer_id || null,
        category: form.category,
        title: form.title.trim(),
        message: form.message.trim(),
        action_url: form.action_url.trim() || null,
      });
      setForm(emptyForm);
      setShowSend(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send notification.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Notifications</h1>
          <p>Keep staff and customer-portal users informed about finance, policy, claims, medical, guarantees and risk events.</p>
        </div>
        <div className="page-actions">
          {data.unread > 0 && <button className="button secondary" disabled={busy} onClick={readAll}>Mark all read</button>}
          {user?.isSuperuser && <button className="button" onClick={() => setShowSend((value) => !value)}>Send notification</button>}
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Inbox</div><div className="value">{data.total}</div><div className="hint">Current filter</div></div>
        <div className="card metric"><div className="label">Unread</div><div className="value">{data.unread}</div><div className="hint">Needs attention</div></div>
        <div className="card metric"><div className="label">Realtime channel</div><div className="value" style={{ fontSize: 20 }}>Enabled</div><div className="hint">User-specific notification events</div></div>
      </section>

      {showSend && user?.isSuperuser && (
        <form className="card pad" onSubmit={sendNotification} style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 16, marginBottom: 16 }}><h2>Send notification</h2></div>
          <div className="form-grid">
            <div className="field full"><label>Recipient</label><select className="select" required value={form.user_id} onChange={(event) => setForm({ ...form, user_id: event.target.value })}><option value="">Select active user</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.email}</option>)}</select></div>
            <div className="field"><label>Category</label><select className="select" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></div>
            <div className="field"><label>Customer context (optional)</label><select className="select" value={form.customer_id} onChange={(event) => setForm({ ...form, customer_id: event.target.value })}><option value="">No customer context</option>{customers.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></div>
            <div className="field full"><label>Title</label><input className="input" required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></div>
            <div className="field full"><label>Message</label><textarea className="textarea" required value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} /></div>
            <div className="field full"><label>Action URL (optional)</label><input className="input" value={form.action_url} onChange={(event) => setForm({ ...form, action_url: event.target.value })} placeholder="/portal or /finance" /></div>
          </div>
          <div className="form-actions"><button type="button" className="button secondary" onClick={() => setShowSend(false)}>Cancel</button><button className="button" disabled={busy}>{busy ? "Sending..." : "Send notification"}</button></div>
        </form>
      )}

      <section className="card">
        <div className="card-header"><div><h2>Notification inbox</h2><p className="muted">Read and archive operational messages.</p></div></div>
        <div className="toolbar">
          <select className="select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option><option value="unread">Unread</option><option value="read">Read</option><option value="archived">Archived</option></select>
          <select className="select" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table className="table"><thead><tr><th>Date</th><th>Category</th><th>Message</th><th>Customer</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {data.items.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.category}</td><td><strong>{item.title}</strong><br /><span className="muted">{item.message}</span>{item.action_url && <><br /><a href={item.action_url}>Open related workspace</a></>}</td><td>{item.customer_id ? customerMap.get(item.customer_id) ?? item.customer_id.slice(0, 8) : "-"}</td><td><strong>{item.status}</strong></td><td><div className="page-actions" style={{ justifyContent: "flex-start" }}>{item.status === "unread" && <button className="button ghost small" disabled={busy} onClick={() => markRead(item)}>Read</button>}{item.status !== "archived" && <button className="button ghost small" disabled={busy} onClick={() => archive(item)}>Archive</button>}</div></td></tr>)}
            {!data.items.length && <tr><td colSpan={6}><div className="empty">No notifications match the current filters.</div></td></tr>}
          </tbody></table>
        </div>
      </section>
    </AppShell>
  );
}
