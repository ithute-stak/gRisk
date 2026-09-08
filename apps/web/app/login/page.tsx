"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { refreshCurrentUser, saveUser } from "@/lib/auth";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void refreshCurrentUser()
      .then((user) => {
        if (active && user) router.replace("/");
      })
      .catch(() => {
        // Login remains available when the current-session check cannot complete.
      });
    return () => {
      active = false;
    };
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(email, password);
      saveUser(user);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="login-hero">
        <div className="login-copy">
          <div className="brand-mark">gR</div>
          <div className="login-eyebrow">Guardrisk 360 · Lesotho</div>
          <h1>Insurance and risk operations, in one clear workspace.</h1>
          <p>Manage customers, quotations, policies, claims, medical aid, guarantees, finance and enterprise risk from the same secure operating platform.</p>
          <div className="login-capabilities" aria-label="Platform capabilities">
            <span>Insurance</span>
            <span>Medical Aid</span>
            <span>Bonds & Guarantees</span>
            <span>Risk Management</span>
          </div>
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <h2>Welcome back</h2>
          <p>Sign in with your gRisk account to continue to Guardrisk 360.</p>
          <form onSubmit={submit}>
            {error && <div className="notice error">{error}</div>}
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input id="email" className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button className="button" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in securely"}</button>
          </form>
          <div className="login-security"><span className="status-dot" /> Secure session · role-based access · audited operations</div>
        </div>
      </section>
    </div>
  );
}
