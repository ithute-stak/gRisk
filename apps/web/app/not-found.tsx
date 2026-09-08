import Link from "next/link";

export default function NotFound() {
  return <div className="screen-center"><div className="card pad" style={{ maxWidth: 520, textAlign: "center" }}><h1>Page not found</h1><p className="muted">The requested gRisk workspace does not exist.</p><Link className="button" href="/">Return to dashboard</Link></div></div>;
}
