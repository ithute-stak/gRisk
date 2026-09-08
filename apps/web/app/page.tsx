"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet } from "@/lib/api";
import type { ClaimList, CustomerList, Policy, QuoteList } from "@/lib/types";

const modules = [
  ["/customers", "Customers", "Customer onboarding, profiles and relationship records.", "CU"],
  ["/quotations", "Quotations", "Build, review and approve insurance quotations.", "QT"],
  ["/policies", "Policies", "Track active cover, premiums and policy expiry.", "PL"],
  ["/claims", "Claims", "Register, triage, assess and settle claims.", "CL"],
  ["/reports", "Reports", "Operational and management reporting workspace.", "RP"],
  ["/finance", "Finance", "Premium, billing and finance operations.", "FN"],
] as const;

export default function DashboardPage() {
  const [metrics, setMetrics] = useState({ customers: 0, quotes: 0, policies: 0, claims: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      apiGet<CustomerList>("/api/v1/customers?page=1&page_size=1"),
      apiGet<QuoteList>("/api/v1/insurance/quotes?page=1&page_size=1"),
      apiGet<Policy[]>("/api/v1/insurance/policies"),
      apiGet<ClaimList>("/api/v1/claims?page=1&page_size=1"),
    ]).then(([customers, quotes, policies, claims]) => {
      if (active) setMetrics({ customers: customers.total, quotes: quotes.total, policies: policies.length, claims: claims.total });
    }).catch((err) => {
      if (active) setError(err instanceof Error ? err.message : "Unable to load dashboard metrics.");
    });
    return () => { active = false; };
  }, []);

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Operations overview</h1>
          <p>Monitor the core insurance workflow from customer onboarding through quotation, policy issuance and claims.</p>
        </div>
        <div className="page-actions"><Link className="button" href="/quotations">New quotation</Link></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 22 }}>
        <div className="card metric"><div className="label">Customers</div><div className="value">{metrics.customers}</div><div className="hint">CRM records</div></div>
        <div className="card metric"><div className="label">Quotations</div><div className="value">{metrics.quotes}</div><div className="hint">All workflow stages</div></div>
        <div className="card metric"><div className="label">Policies</div><div className="value">{metrics.policies}</div><div className="hint">Policy register</div></div>
        <div className="card metric"><div className="label">Claims</div><div className="value">{metrics.claims}</div><div className="hint">Claims register</div></div>
      </section>

      <div className="card-header" style={{ paddingLeft: 0, paddingRight: 0, borderBottom: 0 }}><h2>Workspaces</h2></div>
      <section className="module-grid">
        {modules.map(([href, title, description, code]) => (
          <Link href={href} key={href} className="card module-card">
            <div className="module-code">{code}</div>
            <h3>{title}</h3>
            <p>{description}</p>
          </Link>
        ))}
      </section>
    </AppShell>
  );
}
