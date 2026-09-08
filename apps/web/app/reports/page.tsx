"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet } from "@/lib/api";
import type {
  ClaimsReport,
  ExecutiveReport,
  FinanceReport,
  PortfolioReport,
} from "@/lib/report-types";

const money = new Intl.NumberFormat("en-LS", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value: string): string {
  return `M ${money.format(Number(value || 0))}`;
}

function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function BreakdownCard({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <section className="card pad">
      <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 12 }}>
        <h2>{title}</h2>
      </div>
      {entries.length === 0 ? (
        <p className="muted">No records yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 10 }}>
          {entries.map(([key, value]) => (
            <div key={key} style={{ display: "flex", justifyContent: "space-between", gap: 18 }}>
              <span>{label(key)}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function ReportsPage() {
  const [executive, setExecutive] = useState<ExecutiveReport | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioReport | null>(null);
  const [finance, setFinance] = useState<FinanceReport | null>(null);
  const [claims, setClaims] = useState<ClaimsReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const [executiveData, portfolioData, financeData, claimsData] = await Promise.all([
        apiGet<ExecutiveReport>("/api/v1/reports/executive"),
        apiGet<PortfolioReport>("/api/v1/reports/portfolio"),
        apiGet<FinanceReport>("/api/v1/reports/finance"),
        apiGet<ClaimsReport>("/api/v1/reports/claims"),
      ]);
      setExecutive(executiveData);
      setPortfolio(portfolioData);
      setFinance(financeData);
      setClaims(claimsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load management reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Management Reports</h1>
          <p>Executive, portfolio, claims and finance reporting across the Guardrisk operating platform.</p>
        </div>
        <div className="page-actions">
          <button className="button secondary" onClick={() => void load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Customers</div><div className="value">{executive?.customers ?? 0}</div><div className="hint">CRM portfolio</div></div>
        <div className="card metric"><div className="label">Active policies</div><div className="value">{executive?.active_policies ?? 0}</div><div className="hint">Current insurance cover</div></div>
        <div className="card metric"><div className="label">Open claims</div><div className="value">{executive?.open_claims ?? 0}</div><div className="hint">General insurance claims</div></div>
        <div className="card metric"><div className="label">Medical members</div><div className="value">{executive?.active_medical_members ?? 0}</div><div className="hint">Active membership</div></div>
        <div className="card metric"><div className="label">Guarantees</div><div className="value">{executive?.active_guarantees ?? 0}</div><div className="hint">Open guarantee exposure</div></div>
        <div className="card metric"><div className="label">Open risks</div><div className="value">{executive?.open_risk_items ?? 0}</div><div className="hint">Risk register items</div></div>
      </section>

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Policy premium</div><div className="value" style={{ fontSize: 25 }}>{formatMoney(executive?.total_policy_premium ?? "0")}</div><div className="hint">Recorded policy premium</div></div>
        <div className="card metric"><div className="label">Total claimed</div><div className="value" style={{ fontSize: 25 }}>{formatMoney(executive?.total_claimed ?? "0")}</div><div className="hint">General claims submitted</div></div>
        <div className="card metric"><div className="label">Payments received</div><div className="value" style={{ fontSize: 25 }}>{formatMoney(executive?.total_received ?? "0")}</div><div className="hint">Finance collections</div></div>
        <div className="card metric"><div className="label">Outstanding</div><div className="value" style={{ fontSize: 25 }}>{formatMoney(executive?.outstanding_balance ?? "0")}</div><div className="hint">Issued invoice balance</div></div>
      </section>

      <div className="grid two" style={{ marginBottom: 20 }}>
        <section className="card pad">
          <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 12 }}><h2>Finance position</h2></div>
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Total invoiced</span><strong>{formatMoney(finance?.total_invoiced ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Total received</span><strong>{formatMoney(finance?.total_received ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Outstanding balance</span><strong>{formatMoney(finance?.outstanding_balance ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Overdue balance</span><strong>{formatMoney(finance?.overdue_balance ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Overdue invoices</span><strong>{finance?.overdue_invoices ?? 0}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Payments recorded</span><strong>{finance?.payments ?? 0}</strong></div>
          </div>
        </section>

        <section className="card pad">
          <div className="card-header" style={{ padding: 0, paddingBottom: 14, marginBottom: 12 }}><h2>Claims position</h2></div>
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>General claims</span><strong>{claims?.general_claims ?? 0}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Open general claims</span><strong>{claims?.open_general_claims ?? 0}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>General claimed</span><strong>{formatMoney(claims?.general_claimed ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>General approved</span><strong>{formatMoney(claims?.general_approved ?? "0")}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Medical claims</span><strong>{claims?.medical_claims ?? 0}</strong></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Open medical claims</span><strong>{claims?.open_medical_claims ?? 0}</strong></div>
          </div>
        </section>
      </div>

      {portfolio && (
        <div className="grid two">
          <BreakdownCard title="Policies by status" values={portfolio.policies_by_status} />
          <BreakdownCard title="Claims by status" values={portfolio.claims_by_status} />
          <BreakdownCard title="Medical claims by status" values={portfolio.medical_claims_by_status} />
          <BreakdownCard title="Guarantees by status" values={portfolio.guarantees_by_status} />
          <BreakdownCard title="Risk exposure by level" values={portfolio.risk_items_by_level} />
          <BreakdownCard title="Invoices by status" values={portfolio.invoices_by_status} />
          <BreakdownCard title="Quotations by status" values={portfolio.quotes_by_status} />
        </div>
      )}
    </AppShell>
  );
}
