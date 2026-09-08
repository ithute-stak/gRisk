"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiGet } from "@/lib/api";
import type { CustomerList, InsuranceProduct, Policy } from "@/lib/types";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [products, setProducts] = useState<InsuranceProduct[]>([]);
  const [customers, setCustomers] = useState<CustomerList>({ items: [], total: 0, page: 1, page_size: 100 });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<Policy[]>(`/api/v1/insurance/policies${status ? `?policy_status=${encodeURIComponent(status)}` : ""}`),
      apiGet<InsuranceProduct[]>("/api/v1/insurance/products?active_only=false"),
      apiGet<CustomerList>("/api/v1/customers?page=1&page_size=100"),
    ]).then(([policyData, productData, customerData]) => {
      setPolicies(policyData);
      setProducts(productData);
      setCustomers(customerData);
      setError("");
    }).catch((err) => setError(err instanceof Error ? err.message : "Unable to load policies."));
  }, [status]);

  const customerMap = useMemo(() => new Map(customers.items.map((item) => [item.id, item.display_name])), [customers]);
  const productMap = useMemo(() => new Map(products.map((item) => [item.id, item.name])), [products]);
  const active = policies.filter((item) => item.status === "active").length;
  const expiring = policies.filter((item) => {
    const days = (new Date(item.end_date).getTime() - Date.now()) / 86400000;
    return days >= 0 && days <= 30;
  }).length;
  const premium = policies.reduce((sum, item) => sum + Number(item.premium || 0), 0);

  return (
    <AppShell>
      <div className="page-head">
        <div><h1>Policies</h1><p>View issued policies, cover periods, premiums and upcoming expiries.</p></div>
      </div>
      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="grid metrics" style={{ marginBottom: 20 }}>
        <div className="card metric"><div className="label">Policies</div><div className="value">{policies.length}</div><div className="hint">Current filtered register</div></div>
        <div className="card metric"><div className="label">Active</div><div className="value">{active}</div><div className="hint">Active cover</div></div>
        <div className="card metric"><div className="label">Expiring in 30 days</div><div className="value">{expiring}</div><div className="hint">Renewal attention</div></div>
        <div className="card metric"><div className="label">Premium total</div><div className="value" style={{ fontSize: "1.35rem" }}>LSL {premium.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div><div className="hint">Filtered policy premium</div></div>
      </section>

      <section className="card">
        <div className="toolbar">
          <div className="muted" style={{ flex: 1 }}>Policy register</div>
          <select className="select" style={{ width: 180 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{["active","pending","expired","cancelled","suspended"].map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Policy</th><th>Customer</th><th>Product</th><th>Cover</th><th>Sum insured</th><th>Premium</th><th>Status</th></tr></thead>
            <tbody>{policies.map((policy) => (
              <tr key={policy.id}>
                <td><div className="cell-title">{policy.policy_number}</div><div className="cell-sub">Issued {new Date(policy.created_at).toLocaleDateString()}</div></td>
                <td>{customerMap.get(policy.customer_id) || policy.customer_id.slice(0, 8)}</td>
                <td>{productMap.get(policy.product_id) || policy.product_id.slice(0, 8)}</td>
                <td>{new Date(policy.start_date).toLocaleDateString()} – {new Date(policy.end_date).toLocaleDateString()}</td>
                <td className="money">{policy.currency} {Number(policy.sum_insured).toLocaleString()}</td>
                <td className="money">{policy.currency} {Number(policy.premium).toLocaleString()}</td>
                <td><span className={`badge ${policy.status}`}>{policy.status}</span></td>
              </tr>
            ))}</tbody>
          </table>
          {!policies.length && <div className="empty"><strong>No policies found</strong>Accepted quotations can be issued as policies from the Quotations workspace.</div>}
        </div>
      </section>
    </AppShell>
  );
}
