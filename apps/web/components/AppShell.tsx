"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Protected from "@/components/Protected";
import { SmartDialog } from "@/components/SmartUi";
import { currentUser } from "@/lib/auth";
import { logout } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

const staffRoleNames = new Set(["superadmin", "admin", "broker", "claims", "medical", "finance", "risk", "viewer"]);

const staffNavigation = [
  ["/", "Dashboard", "DB"],
  ["/customers", "Customers", "CU"],
  ["/quotations", "Quotations", "QT"],
  ["/policies", "Policies", "PL"],
  ["/claims", "Claims", "CL"],
  ["/medical", "Medical Aid", "MD"],
  ["/bonds", "Bonds & Guarantees", "BG"],
  ["/risk", "Risk Management", "RK"],
  ["/finance", "Finance", "FN"],
  ["/documents", "Documents", "DC"],
  ["/document-studio", "Document Studio", "DS"],
  ["/partners", "Partners", "PR"],
  ["/notifications", "Notifications", "NT"],
  ["/portal", "Customer Portal", "PT"],
  ["/reports", "Reports", "RP"],
] as const;

const adminNavigation = ["/admin", "Administration", "AD"] as const;

const portalNavigation = [
  ["/portal", "My Cover", "MC"],
  ["/notifications", "Notifications", "NT"],
] as const;

function isStaffUser(user: AuthUser | null): boolean {
  if (!user) return false;
  return user.isSuperuser || user.roles.some((role) => staffRoleNames.has(role));
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    const syncUser = () => setUser(currentUser());
    syncUser();
    window.addEventListener("grisk-session", syncUser);
    return () => window.removeEventListener("grisk-session", syncUser);
  }, [pathname]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
        setProfileOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const staff = isStaffUser(user);
  const navigation = useMemo(
    () => (staff ? (user?.isSuperuser ? [...staffNavigation, adminNavigation] : [...staffNavigation]) : [...portalNavigation]),
    [staff, user?.isSuperuser],
  );
  const userName = user?.name || user?.email || "gRisk user";
  const roleLabel = user?.isSuperuser ? "Super administrator" : user?.roles?.[0]?.replaceAll("_", " ") || "Portal user";
  const activeEntry = navigation.find(([href]) => (href === "/" ? pathname === "/" : pathname.startsWith(href)));
  const activeLabel = activeEntry?.[1] || (staff ? "Guardrisk Operations" : "Customer Portal");
  const commandItems = navigation.filter(([, label]) => label.toLowerCase().includes(commandQuery.trim().toLowerCase()));

  async function signOut() {
    setProfileOpen(false);
    await logout();
    router.replace("/login");
  }

  return (
    <Protected>
      <div className="app-shell">
        <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
          <div className="brand-block">
            <div className="brand-mark">gR</div>
            <div>
              <strong>gRisk</strong>
              <span>{staff ? "Guardrisk 360" : "Customer Portal"}</span>
            </div>
          </div>

          <div className="sidebar-label">{staff ? "Operations" : "My workspace"}</div>
          <nav className="side-nav" aria-label="Main navigation">
            {navigation.map(([href, label, short]) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link key={href} href={href} className={active ? "nav-item active" : "nav-item"} onClick={() => setOpen(false)}>
                  <span className="nav-icon">{short}</span>
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="sidebar-foot">
            <div className="sidebar-status"><span className="status-dot" /> Secure workspace</div>
            <small>gRisk 1.0 · Guardrisk Lesotho</small>
          </div>
        </aside>

        {open && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setOpen(false)} />}

        <div className="workspace">
          <header className="topbar">
            <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="Open navigation">☰</button>
            <div className="topbar-context">
              <strong>{activeLabel}</strong>
              <span>{staff ? "Guardrisk 360 · Lesotho" : "Secure customer access"}</span>
            </div>

            <button
              type="button"
              className="command-trigger"
              onClick={() => {
                setCommandOpen(true);
                setProfileOpen(false);
              }}
              aria-label="Search workspaces"
            >
              <span className="command-symbol" aria-hidden="true">⌕</span>
              <span>Search workspaces</span>
              <kbd>Ctrl K</kbd>
            </button>

            <div className="topbar-user">
              <button
                type="button"
                className="profile-trigger"
                onClick={() => setProfileOpen((value) => !value)}
                aria-expanded={profileOpen}
                aria-haspopup="menu"
              >
                <div className="user-avatar">{userName.slice(0, 1).toUpperCase()}</div>
                <span className="profile-copy">
                  <strong>{userName}</strong>
                  <small>{roleLabel}</small>
                </span>
                <span className="profile-chevron" aria-hidden="true">⌄</span>
              </button>

              {profileOpen && (
                <div className="profile-popover" role="menu">
                  <div className="profile-popover-head">
                    <div className="user-avatar large">{userName.slice(0, 1).toUpperCase()}</div>
                    <div>
                      <strong>{userName}</strong>
                      <span>{user?.email || roleLabel}</span>
                    </div>
                  </div>
                  <div className="profile-role-row">
                    {(user?.roles || []).slice(0, 3).map((role) => <span key={role} className="mini-chip">{role.replaceAll("_", " ")}</span>)}
                    {user?.isSuperuser && <span className="mini-chip accent">superadmin</span>}
                  </div>
                  <button className="profile-menu-item danger-text" type="button" onClick={() => void signOut()}>Sign out</button>
                </div>
              )}
            </div>
          </header>

          <main className="page-container">{children}</main>
        </div>
      </div>

      <SmartDialog
        open={commandOpen}
        onClose={() => {
          setCommandOpen(false);
          setCommandQuery("");
        }}
        title="Jump to a workspace"
        description="Find any gRisk area without leaving your current workflow."
        size="sm"
      >
        <div className="command-palette">
          <div className="command-search-wrap">
            <span aria-hidden="true">⌕</span>
            <input
              className="command-search"
              value={commandQuery}
              onChange={(event) => setCommandQuery(event.target.value)}
              placeholder="Type a workspace name…"
              aria-label="Search workspaces"
            />
            <kbd>Esc</kbd>
          </div>
          <div className="command-list">
            {commandItems.map(([href, label, short]) => (
              <Link
                key={href}
                href={href}
                className="command-item"
                onClick={() => {
                  setCommandOpen(false);
                  setCommandQuery("");
                }}
              >
                <span className="command-item-icon">{short}</span>
                <span>
                  <strong>{label}</strong>
                  <small>{href === "/" ? "Overview" : href.replace("/", "")}</small>
                </span>
                <span className="command-arrow" aria-hidden="true">→</span>
              </Link>
            ))}
            {!commandItems.length && <div className="command-empty">No workspace matches “{commandQuery}”.</div>}
          </div>
        </div>
      </SmartDialog>
    </Protected>
  );
}
