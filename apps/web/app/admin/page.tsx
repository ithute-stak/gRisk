"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import type { AdminRole, AdminUser, AdminUserList, AuditEventList } from "@/lib/admin-types";

const emptyCreate = {
  email: "",
  full_name: "",
  password: "",
  role_names: [] as string[],
  is_active: true,
  is_superuser: false,
};

function humanize(value: string): string {
  return value.replaceAll("_", " ").replaceAll(".", " · ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminPage() {
  const sessionUser = currentUser();
  const [tab, setTab] = useState<"users" | "audit">("users");
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [users, setUsers] = useState<AdminUserList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [audit, setAudit] = useState<AuditEventList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState(emptyCreate);
  const [editRoles, setEditRoles] = useState<string[]>([]);
  const [editName, setEditName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [search, setSearch] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selected = useMemo(
    () => users.items.find((user) => user.id === selectedId) ?? null,
    [selectedId, users.items],
  );

  const loadUsers = useCallback(async () => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (search.trim()) params.set("q", search.trim());
    if (activeFilter) params.set("active", activeFilter);
    const [roleData, userData] = await Promise.all([
      apiGet<AdminRole[]>("/api/v1/admin/roles"),
      apiGet<AdminUserList>(`/api/v1/admin/users?${params.toString()}`),
    ]);
    setRoles(roleData);
    setUsers(userData);
  }, [activeFilter, search]);

  const loadAudit = useCallback(async () => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (auditSearch.trim()) params.set("q", auditSearch.trim());
    const data = await apiGet<AuditEventList>(`/api/v1/admin/audit?${params.toString()}`);
    setAudit(data);
  }, [auditSearch]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      await Promise.all([loadUsers(), loadAudit()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load administration workspace.");
    } finally {
      setLoading(false);
    }
  }, [loadAudit, loadUsers]);

  useEffect(() => {
    if (!sessionUser?.isSuperuser) {
      setLoading(false);
      return;
    }
    const timer = setTimeout(() => void load(), 120);
    return () => clearTimeout(timer);
  }, [load, sessionUser?.isSuperuser]);

  useEffect(() => {
    if (!selected) return;
    setEditName(selected.full_name);
    setEditRoles(selected.roles);
    setNewPassword("");
  }, [selected]);

  function toggleRole(roleName: string, mode: "create" | "edit") {
    if (mode === "create") {
      setCreateForm((current) => ({
        ...current,
        role_names: current.role_names.includes(roleName)
          ? current.role_names.filter((role) => role !== roleName)
          : [...current.role_names, roleName],
      }));
      return;
    }
    setEditRoles((current) =>
      current.includes(roleName) ? current.filter((role) => role !== roleName) : [...current, roleName],
    );
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await apiPost<AdminUser>("/api/v1/admin/users", createForm);
      setCreateForm(emptyCreate);
      setShowCreate(false);
      setNotice(`Created ${created.full_name}.`);
      await loadUsers();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user.");
    } finally {
      setBusy(false);
    }
  }

  async function saveSelected() {
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await apiPatch<AdminUser>(`/api/v1/admin/users/${selected.id}`, {
        full_name: editName,
        role_names: editRoles,
      });
      setNotice(`Updated ${updated.full_name}.`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update user.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleAccount(field: "is_active" | "is_superuser") {
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await apiPatch<AdminUser>(`/api/v1/admin/users/${selected.id}`, {
        [field]: !selected[field],
      });
      setNotice(`Updated ${updated.full_name}.`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update account.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiPost<void>(`/api/v1/admin/users/${selected.id}/reset-password`, { password: newPassword });
      setNewPassword("");
      setNotice(`Password reset for ${selected.full_name}.`);
      await loadAudit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    } finally {
      setBusy(false);
    }
  }

  if (!sessionUser?.isSuperuser) {
    return (
      <AppShell>
        <div className="page-head">
          <div>
            <h1>Administration</h1>
            <p>Platform administration is restricted to Guardrisk superusers.</p>
          </div>
        </div>
        <div className="notice error">Your account does not have superuser access to this workspace.</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Administration</h1>
          <p>Manage users, access roles, account status, password resets and the platform audit trail.</p>
        </div>
        <div className="page-actions">
          <button className="button secondary" onClick={() => void load()} disabled={loading || busy}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button className="button" onClick={() => setShowCreate((value) => !value)}>
            {showCreate ? "Close form" : "New user"}
          </button>
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 14 }}>{error}</div>}
      {notice && <div className="notice" style={{ marginBottom: 14 }}>{notice}</div>}

      <section className="grid metrics" style={{ marginBottom: 18 }}>
        <div className="card metric"><div className="label">Users</div><div className="value">{users.total}</div><div className="hint">Platform identities</div></div>
        <div className="card metric"><div className="label">Active</div><div className="value">{users.items.filter((u) => u.is_active).length}</div><div className="hint">In current result set</div></div>
        <div className="card metric"><div className="label">Superusers</div><div className="value">{users.items.filter((u) => u.is_superuser).length}</div><div className="hint">Privileged accounts</div></div>
        <div className="card metric"><div className="label">Roles</div><div className="value">{roles.length}</div><div className="hint">Controlled access profiles</div></div>
      </section>

      <div className="page-actions" style={{ marginBottom: 16 }}>
        <button className={tab === "users" ? "button" : "button secondary"} onClick={() => setTab("users")}>Users & access</button>
        <button className={tab === "audit" ? "button" : "button secondary"} onClick={() => setTab("audit")}>Audit trail</button>
      </div>

      {showCreate && (
        <section className="card pad" style={{ marginBottom: 18 }}>
          <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 16 }}><h2>Create platform user</h2></div>
          <form onSubmit={createUser}>
            <div className="form-grid">
              <div className="field"><label>Full name</label><input className="input" required minLength={2} value={createForm.full_name} onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })} /></div>
              <div className="field"><label>Email</label><input className="input" type="email" required value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} /></div>
              <div className="field full"><label>Temporary password</label><input className="input" type="password" required minLength={12} value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} /></div>
              <div className="field full">
                <label>Roles</label>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {roles.map((role) => (
                    <label key={role.id} style={{ display: "inline-flex", alignItems: "center", gap: 6, border: "1px solid var(--line)", borderRadius: 9, padding: "7px 9px", background: "white" }}>
                      <input type="checkbox" checked={createForm.role_names.includes(role.name)} onChange={() => toggleRole(role.name, "create")} />
                      <span>{humanize(role.name)}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="field full">
                <label style={{ display: "inline-flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={createForm.is_superuser} onChange={(e) => setCreateForm({ ...createForm, is_superuser: e.target.checked })} /> Grant superuser access</label>
              </div>
            </div>
            <div className="form-actions"><button className="button" disabled={busy}>{busy ? "Creating…" : "Create user"}</button></div>
          </form>
        </section>
      )}

      {tab === "users" ? (
        <div className="grid two">
          <section className="card">
            <div className="toolbar">
              <input className="input search" placeholder="Search name or email" value={search} onChange={(e) => setSearch(e.target.value)} />
              <select className="select" style={{ width: 150 }} value={activeFilter} onChange={(e) => setActiveFilter(e.target.value)}>
                <option value="">All accounts</option><option value="true">Active</option><option value="false">Inactive</option>
              </select>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>User</th><th>Access</th><th>Status</th></tr></thead>
                <tbody>
                  {users.items.map((user) => (
                    <tr key={user.id} onClick={() => setSelectedId(user.id)} style={{ cursor: "pointer", background: selectedId === user.id ? "#f0f8f6" : undefined }}>
                      <td><div className="cell-title">{user.full_name}</div><div className="cell-sub">{user.email}</div></td>
                      <td><div className="cell-title">{user.is_superuser ? "Superuser" : user.roles.map(humanize).join(", ") || "Portal only"}</div></td>
                      <td><span className={`badge ${user.is_active ? "active" : "cancelled"}`}>{user.is_active ? "active" : "inactive"}</span></td>
                    </tr>
                  ))}
                  {!loading && users.items.length === 0 && <tr><td colSpan={3}><div className="empty"><strong>No users found</strong>Adjust the search or create a user.</div></td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card pad">
            {!selected ? (
              <div className="empty"><strong>Select a user</strong>Choose an account to manage roles, status or credentials.</div>
            ) : (
              <>
                <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 16 }}>
                  <div><h2>{selected.full_name}</h2><div className="cell-sub">{selected.email}</div></div>
                  <span className={`badge ${selected.is_active ? "active" : "cancelled"}`}>{selected.is_active ? "active" : "inactive"}</span>
                </div>
                <div className="field" style={{ marginBottom: 14 }}><label>Full name</label><input className="input" value={editName} onChange={(e) => setEditName(e.target.value)} /></div>
                <div className="field" style={{ marginBottom: 16 }}>
                  <label>Assigned roles</label>
                  <div style={{ display: "grid", gap: 8 }}>
                    {roles.map((role) => (
                      <label key={role.id} style={{ display: "flex", gap: 9, alignItems: "flex-start", padding: "8px 0", borderBottom: "1px solid #edf1f4" }}>
                        <input type="checkbox" checked={editRoles.includes(role.name)} onChange={() => toggleRole(role.name, "edit")} />
                        <span><strong style={{ display: "block", fontSize: ".83rem" }}>{humanize(role.name)}</strong><small className="muted">{role.description || "No description"}</small></span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="actions" style={{ marginBottom: 20 }}>
                  <button className="button" onClick={() => void saveSelected()} disabled={busy || editName.trim().length < 2}>Save profile & roles</button>
                  <button className="button secondary" onClick={() => void toggleAccount("is_active")} disabled={busy || selected.id === sessionUser.id}>{selected.is_active ? "Deactivate" : "Activate"}</button>
                  <button className="button secondary" onClick={() => void toggleAccount("is_superuser")} disabled={busy || selected.id === sessionUser.id}>{selected.is_superuser ? "Remove superuser" : "Make superuser"}</button>
                </div>
                <form onSubmit={resetPassword}>
                  <div className="field"><label>Reset password</label><input className="input" type="password" minLength={12} required placeholder="Minimum 12 characters" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></div>
                  <div className="form-actions"><button className="button secondary" disabled={busy || newPassword.length < 12}>Reset password</button></div>
                </form>
              </>
            )}
          </section>
        </div>
      ) : (
        <section className="card">
          <div className="toolbar"><input className="input search" placeholder="Search action, entity type or entity ID" value={auditSearch} onChange={(e) => setAuditSearch(e.target.value)} /></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>Action</th><th>Entity</th><th>Actor</th><th>Source</th></tr></thead>
              <tbody>
                {audit.items.map((event) => (
                  <tr key={event.id}>
                    <td>{formatTime(event.created_at)}</td>
                    <td><div className="cell-title">{humanize(event.action)}</div><div className="cell-sub">{Object.keys(event.details || {}).slice(0, 4).join(", ") || "No extra details"}</div></td>
                    <td><div className="cell-title">{humanize(event.entity_type)}</div><div className="cell-sub">{event.entity_id || "—"}</div></td>
                    <td><span className="cell-sub">{event.actor_user_id || "System"}</span></td>
                    <td>{event.ip_address || "—"}</td>
                  </tr>
                ))}
                {!loading && audit.items.length === 0 && <tr><td colSpan={5}><div className="empty"><strong>No audit events found</strong>No entries match the current filter.</div></td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </AppShell>
  );
}
