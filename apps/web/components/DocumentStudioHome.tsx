"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActionMenu, SmartDialog } from "@/components/SmartUi";
import {
  createStudioDocument,
  deleteStudioDocument,
  listStudioDocuments,
  type StudioDocument,
} from "@/lib/studio";

type Category = "All" | "Popular" | "Insurance" | "Claims" | "Medical" | "Business" | "Risk" | "Legal";

type Template = {
  key: string;
  title: string;
  description: string;
  category: Exclude<Category, "All">;
  badge?: string;
  style: string;
  html: string;
};

const templates: Template[] = [
  { key: "blank", title: "Blank document", description: "A clean Guardrisk page with the complete Word-like ribbon and signing tools.", category: "Popular", badge: "Start fresh", style: "guardrisk_orange", html: "<p><br></p>" },
  { key: "formal_letter", title: "Formal letter", description: "Professional correspondence with recipient, subject, body and signature section.", category: "Popular", badge: "Most used", style: "guardrisk_orange", html: "<p><strong>Date:</strong> {{date}}</p><p><strong>To:</strong> Recipient name<br>Organisation<br>Maseru, Lesotho</p><p><strong>RE: SUBJECT OF LETTER</strong></p><p>Dear Sir/Madam,</p><p>Type your letter here.</p><p>Yours faithfully,</p><p><strong>Authorised Signatory</strong><br>Guardrisk Insurance Brokers</p>" },
  { key: "quotation_cover", title: "Quotation cover letter", description: "Client-facing cover letter for an insurance quotation or placement submission.", category: "Insurance", badge: "Insurance", style: "guardrisk_orange", html: "<h1>Insurance Quotation</h1><p><strong>Client:</strong> </p><p><strong>Reference:</strong> </p><p>Dear Client,</p><p>We are pleased to present the following insurance quotation for your consideration.</p><h2>Cover Summary</h2><p>Describe the proposed cover, limits, premium and important conditions.</p><h2>Requirements</h2><ul><li>Supporting documents</li><li>Acceptance confirmation</li></ul><p>Yours faithfully,</p>" },
  { key: "policy_letter", title: "Policy correspondence", description: "Formal policy issue, amendment, renewal or cancellation correspondence.", category: "Insurance", style: "classic", html: "<h1>Policy Correspondence</h1><p><strong>Policy number:</strong> </p><p><strong>Insured:</strong> </p><p>Dear Client,</p><p>We write regarding the above insurance policy.</p><h2>Policy Update</h2><p>Enter the policy update here.</p><p>Yours faithfully,</p>" },
  { key: "claim_letter", title: "Claims letter", description: "Claim acknowledgement, document request, assessment or settlement correspondence.", category: "Claims", badge: "Workflow", style: "classic", html: "<h1>Claim Correspondence</h1><p><strong>Claim number:</strong> </p><p><strong>Policy number:</strong> </p><p>Dear Client,</p><p>We refer to the claim noted above.</p><h2>Next Steps</h2><p>Enter the required claim action or decision here.</p><p>Yours faithfully,</p>" },
  { key: "medical_letter", title: "Medical aid letter", description: "Member, benefit, authorisation or medical claim correspondence.", category: "Medical", badge: "Health", style: "clean", html: "<h1>Medical Aid Correspondence</h1><p><strong>Member:</strong> </p><p><strong>Member number:</strong> </p><p>Dear Member,</p><p>We write regarding your Guardrisk Health membership.</p><h2>Details</h2><p>Enter the benefit, authorisation or claim details here.</p><p>Kind regards,</p>" },
  { key: "memo", title: "Memorandum", description: "Internal communication with purpose, background, decisions and actions.", category: "Business", style: "clean", html: "<h1>Memorandum</h1><p><strong>To:</strong> </p><p><strong>From:</strong> </p><p><strong>Date:</strong> </p><p><strong>Subject:</strong> </p><h2>Purpose</h2><p></p><h2>Background</h2><p></p><h2>Actions</h2><ul><li></li></ul>" },
  { key: "meeting_minutes", title: "Meeting minutes", description: "Attendance, agenda, resolutions, owners and deadlines.", category: "Business", style: "clean", html: "<h1>Meeting Minutes</h1><p><strong>Date:</strong> </p><p><strong>Venue:</strong> </p><p><strong>Chair:</strong> </p><h2>Attendance</h2><ul><li></li></ul><h2>Agenda</h2><ol><li></li></ol><h2>Resolutions and Actions</h2><p></p>" },
  { key: "risk_report", title: "Risk assessment report", description: "Executive risk report with findings, controls and recommendations.", category: "Risk", badge: "Risk", style: "executive", html: "<h1>Risk Assessment Report</h1><h2>Executive Summary</h2><p></p><h2>Scope</h2><p></p><h2>Key Risks</h2><ol><li></li></ol><h2>Existing Controls</h2><p></p><h2>Recommendations</h2><p></p>" },
  { key: "proposal", title: "Professional proposal", description: "Executive proposal covering problem, solution, scope, implementation and pricing.", category: "Business", badge: "Cover page", style: "executive", html: "<h1>Professional Proposal</h1><p><strong>Prepared for:</strong> </p><p><strong>Prepared by:</strong> Guardrisk Insurance Brokers</p><h2>Executive Summary</h2><p></p><h2>Proposed Solution</h2><p></p><h2>Scope and Deliverables</h2><p></p><h2>Implementation</h2><p></p><h2>Commercial Proposal</h2><p></p>" },
  { key: "contract", title: "General agreement", description: "Parties, obligations, payment, termination, dispute terms and signature fields.", category: "Legal", style: "legal", html: "<h1>Agreement</h1><p>This Agreement is entered into between:</p><p><strong>Party A:</strong> </p><p><strong>Party B:</strong> </p><h2>1. Purpose</h2><p></p><h2>2. Obligations</h2><p></p><h2>3. Payment</h2><p></p><h2>4. Termination</h2><p></p><h2>5. Dispute Resolution</h2><p></p><p>[[SIGNATURE:Authorised Signatory]]</p>" },
  { key: "certificate", title: "Certificate", description: "A polished completion or recognition certificate.", category: "Business", style: "elegant", html: "<h1 style=\"text-align:center\">CERTIFICATE</h1><p style=\"text-align:center\">This is to certify that</p><h2 style=\"text-align:center\">Recipient Name</h2><p style=\"text-align:center\">has successfully completed / achieved</p><h2 style=\"text-align:center\">Achievement</h2><p style=\"text-align:center\">[[SIGNATURE:Authorised Signatory]]</p>" },
];

const categories: Category[] = ["All", "Popular", "Insurance", "Claims", "Medical", "Business", "Risk", "Legal"];

function plainText(html: string) {
  if (typeof document === "undefined") return html.replace(/<[^>]+>/g, " ");
  const node = document.createElement("div");
  node.innerHTML = html;
  return node.textContent || "";
}

export default function DocumentStudioHome() {
  const router = useRouter();
  const [documents, setDocuments] = useState<StudioDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState<Category>("All");
  const [deleteTarget, setDeleteTarget] = useState<StudioDocument | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDocuments(await listStudioDocuments(search, status));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load Document Studio.");
    } finally {
      setLoading(false);
    }
  }, [search, status]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 180); return () => window.clearTimeout(timer); }, [load]);

  const visibleTemplates = useMemo(() => templates.filter((item) => category === "All" || item.category === category), [category]);

  async function create(template: Template) {
    setCreating(template.key);
    setError("");
    try {
      const created = await createStudioDocument({
        title: template.key === "blank" ? "Untitled document" : `New ${template.title.toLowerCase()}`,
        template_key: template.key,
        style_key: template.style,
        html_content: template.html,
        plain_text: plainText(template.html),
        settings: { page_size: "a4", orientation: "portrait", margin_mm: 20, theme: template.style, brand_header: true },
        visibility: "private",
      });
      router.push(`/document-studio/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create document.");
    } finally {
      setCreating(null);
    }
  }

  async function remove() {
    if (!deleteTarget) return;
    try {
      await deleteStudioDocument(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete document.");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Document Studio</h1>
          <p>LoanHub-style Word workspace adapted for Guardrisk: templates, rich editing, page layout, signing fields, autosave, revisions, sharing and PDF/Word export.</p>
        </div>
        <div className="page-actions"><button className="button" onClick={() => void create(templates[0])} disabled={Boolean(creating)}>Blank document</button></div>
      </div>

      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="studio-office-hero card">
        <div className="studio-office-hero-copy"><span>DOCUMENT STUDIO</span><h2>Create a new document</h2><p>Start with a Guardrisk template or a blank page. Everything remains editable in the Word-like workspace.</p></div>
        <div className="studio-office-g">G</div>
      </section>

      <div className="studio-category-row">
        {categories.map((item) => <button key={item} className={category === item ? "studio-category active" : "studio-category"} onClick={() => setCategory(item)}>{item}</button>)}
      </div>

      <section className="studio-template-grid">
        {visibleTemplates.map((template) => (
          <button key={template.key} className="studio-template-card card" onClick={() => void create(template)} disabled={Boolean(creating)}>
            <div className="studio-template-preview"><div className="studio-template-g">G</div><div className="studio-template-lines"><i /><i /><i /><i /></div></div>
            <div className="studio-template-copy"><strong>{template.title}</strong>{template.badge && <span>{template.badge}</span>}<p>{template.description}</p></div>
            {creating === template.key && <div className="studio-template-loading">Creating…</div>}
          </button>
        ))}
      </section>

      <section className="card studio-recent-card">
        <div className="card-header"><div><h2>Recent documents</h2><p>Autosaved workspace documents and shared team work.</p></div></div>
        <div className="toolbar">
          <input className="input search" placeholder="Search documents…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ width: 160 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="draft">Draft</option><option value="review">Review</option><option value="final">Final</option><option value="archived">Archived</option></select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Template</th><th>Status</th><th>Access</th><th>Version</th><th>Modified</th><th aria-label="Actions" /></tr></thead>
            <tbody>{documents.map((item) => <tr key={item.id}>
              <td><button className="studio-document-link" onClick={() => router.push(`/document-studio/${item.id}`)}><strong>{item.title}</strong><small>{item.plain_text.slice(0, 90) || "Empty document"}</small></button></td>
              <td>{item.template_key.replaceAll("_", " ")}</td>
              <td><span className={`badge ${item.status === "final" ? "active" : item.status}`}>{item.status}</span></td>
              <td>{item.visibility === "team" ? "Team" : "Private"}{!item.can_edit ? " · view only" : ""}</td>
              <td>v{item.version}</td>
              <td>{new Date(item.updated_at).toLocaleString()}</td>
              <td><ActionMenu label={`Actions for ${item.title}`}><button className="action-menu-item" onClick={() => router.push(`/document-studio/${item.id}`)}>Open document</button>{item.can_edit && <button className="action-menu-item danger" onClick={() => setDeleteTarget(item)}>Delete</button>}</ActionMenu></td>
            </tr>)}</tbody>
          </table>
          {!loading && !documents.length && <div className="empty"><strong>No documents found</strong>Create your first Guardrisk document from a template above.</div>}
          {loading && <div className="empty">Loading documents…</div>}
        </div>
      </section>

      <SmartDialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} title="Delete document" description="This permanently removes the workspace document and its revision history." size="sm">
        <p className="muted">Delete <strong>{deleteTarget?.title}</strong>?</p>
        <div className="form-actions"><button className="button secondary" onClick={() => setDeleteTarget(null)}>Cancel</button><button className="button danger" onClick={() => void remove()}>Delete document</button></div>
      </SmartDialog>
    </>
  );
}
