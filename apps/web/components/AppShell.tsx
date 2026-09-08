"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, currentUser } from "@/lib/auth";
import Protected from "@/components/Protected";

const navigation = [
  ["/", "Dashboard", "DB"],
  ["/customers", "Customers", "CU"],
  ["/quotations", "Quotations", "QT"],
  ["/policies", "Policies", "PL"],
  ["/claims", "Claims", "CL"],
  ["/reports", "Reports", "RP"],
  ["/finance", "Finance", "FN"],
  ["/risk", "Risk", "RK"],
  ["/admin", "Administration", "AD"],
] as const;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [userName, setUserName] = useState("gRisk user");

  useEffect(() => {
    const user = currentUser();
    setUserName(user?.name || user?.email || "gRisk user");
  }, [pathname]);

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
              <span>Guardrisk Platform</span>
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
            <span>gRisk 0.5</span>
            <small>Next.js + FastAPI</small>
          </div>
        </aside>

        {open && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setOpen(false)} />}

        <div className="workspace">
          <header className="topbar">
            <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="Open navigation">☰</button>
            <div className="topbar-context">
              <strong>Guardrisk Operations</strong>
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
