"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Protected from "@/components/Protected";
import { clearToken, currentUser } from "@/lib/auth";
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
  ["/notifications", "Notifications", "NT"],
  ["/portal", "Customer Portal", "PT"],
  ["/reports", "Reports", "RP"],
  ["/admin", "Administration", "AD"],
] as const;

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

  useEffect(() => {
    setUser(currentUser());
  }, [pathname]);

  const staff = isStaffUser(user);
  const navigation = staff ? staffNavigation : portalNavigation;
  const userName = user?.name || user?.email || "gRisk user";

  function signOut() {
    clearToken();
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
              <span>{staff ? "Guardrisk Platform" : "Customer Portal"}</span>
            </div>
          </div>
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
            <span>gRisk 0.9</span>
            <small>{staff ? "Next.js + FastAPI" : "Secure customer access"}</small>
          </div>
        </aside>

        {open && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setOpen(false)} />}

        <div className="workspace">
          <header className="topbar">
            <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="Open navigation">☰</button>
            <div className="topbar-context">
              <strong>{staff ? "Guardrisk Operations" : "Guardrisk Customer Portal"}</strong>
              <span>Lesotho</span>
            </div>
            <div className="topbar-user">
              <div className="user-avatar">{userName.slice(0, 1).toUpperCase()}</div>
              <span className="user-name">{userName}</span>
              <button className="button ghost small" onClick={signOut}>Sign out</button>
            </div>
          </header>
          <main className="page-container">{children}</main>
        </div>
      </div>
    </Protected>
  );
}
