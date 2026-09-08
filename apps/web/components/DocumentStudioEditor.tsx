"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SmartDialog } from "@/components/SmartUi";
import {
  createStudioCheckpoint,
  downloadStudioDocument,
  getStudioDocument,
  listStudioRevisions,
  saveBlobDownload,
  saveStudioDocument,
  type StudioDocument,
  type StudioRevision,
} from "@/lib/studio";

type RibbonTab = "Home" | "Insert" | "Layout" | "Design";
type SaveState = "saved" | "saving" | "unsaved" | "conflict" | "error";

const fonts = ["Arial", "Calibri", "Georgia", "Times New Roman", "Verdana"];
const sizes = ["10", "11", "12", "14", "16", "18", "24", "32"];
const themes = [
  ["guardrisk_orange", "Guardrisk Orange"],
  ["classic", "Classic Word"],
  ["clean", "Minimal Clean"],
  ["executive", "Executive Charcoal"],
  ["legal", "Legal Monochrome"],
  ["elegant", "Elegant"],
] as const;

function command(name: string, value?: string) {
  document.execCommand(name, false, value);
}

function stripHtml(html: string) {
  const node = document.createElement("div");
  node.innerHTML = html;
  return (node.textContent || "").replace(/\s+/g, " ").trim();
}

function countWords(text: string) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export default function DocumentStudioEditor({ documentId }: { documentId: string }) {
  const router = useRouter();
  const editorRef = useRef<HTMLDivElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const [doc, setDoc] = useState<StudioDocument | null>(null);
  const [title, setTitle] = useState("");
  const [html, setHtml] = useState("");
  const [activeTab, setActiveTab] = useState<RibbonTab>("Home");
  const [font, setFont] = useState("Arial");
  const [fontSize, setFontSize] = useState("11");
  const [zoom, setZoom] = useState(100);
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [revisions, setRevisions] = useState<StudioRevision[]>([]);
  const [exportOpen, setExportOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sidePanel, setSidePanel] = useState<"none" | "fields" | "document">("document");

  const load = useCallback(async () => {
    setError("");
    try {
      const item = await getStudioDocument(documentId);
      setDoc(item);
      setTitle(item.title);
      setHtml(item.html_content);
      if (editorRef.current) editorRef.current.innerHTML = item.html_content;
      setSaveState("saved");
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load document.");
    }
  }, [documentId]);

  useEffect(() => { void load(); }, [load]);

  const save = useCallback(async (manual = false) => {
    if (!doc || !doc.can_edit || (!dirty && !manual)) return;
    const content = editorRef.current?.innerHTML ?? html;
    setSaveState("saving");
    try {
      const updated = await saveStudioDocument(doc.id, {
        title: title.trim() || "Untitled document",
        html_content: content,
        plain_text: stripHtml(content),
        settings: doc.settings,
        style_key: doc.style_key,
        visibility: doc.visibility,
        status: doc.status,
        expected_version: doc.version,
      });
      setDoc(updated);
      setHtml(content);
      setDirty(false);
      setSaveState("saved");
    } catch (err) {
      if (err instanceof Error && err.message.toLowerCase().includes("changed elsewhere")) {
        setSaveState("conflict");
      } else {
        setSaveState("error");
        setError(err instanceof Error ? err.message : "Unable to save document.");
      }
    }
  }, [doc, dirty, html, title]);

  useEffect(() => {
    if (!dirty || !doc?.can_edit || saveState === "conflict") return;
    const timer = window.setTimeout(() => void save(false), 1400);
    return () => window.clearTimeout(timer);
  }, [dirty, doc?.can_edit, save, saveState]);

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void save(true);
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [save]);

  const plain = useMemo(() => (typeof window === "undefined" ? "" : stripHtml(html)), [html]);
  const words = useMemo(() => countWords(plain), [plain]);
  const fieldCount = useMemo(() => (html.match(/data-grisk-field=/g) || []).length, [html]);

  function syncEditor() {
    const next = editorRef.current?.innerHTML || "";
    setHtml(next);
    setDirty(true);
    setSaveState("unsaved");
  }

  function run(cmd: string, value?: string) {
    if (!doc?.can_edit) return;
    editorRef.current?.focus();
    command(cmd, value);
    syncEditor();
  }

  function insertHtml(fragment: string) {
    run("insertHTML", fragment);
  }

  function insertField(type: string, label: string) {
    insertHtml(`<span class="grisk-fill-field" contenteditable="false" data-grisk-field="${type}"><span>${label}</span><strong>${type === "checkbox" ? "☐" : "Click to fill"}</strong></span>&nbsp;`);
  }

  function insertLink() {
    const url = window.prompt("Link URL", "https://");
    if (url?.trim()) run("createLink", url.trim());
  }

  function insertTable() {
    insertHtml('<table class="grisk-editor-table"><tbody><tr><td>Cell 1</td><td>Cell 2</td></tr><tr><td>Cell 3</td><td>Cell 4</td></tr></tbody></table><p><br></p>');
  }

  function insertPageBreak() {
    insertHtml('<div class="grisk-page-break" data-page-break="true" contenteditable="false">PAGE BREAK</div><p>[[PAGE_BREAK]]</p>');
  }

  function chooseImage(file: File | null) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Choose an image file.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => insertHtml(`<img src="${String(reader.result)}" alt="Inserted image" style="max-width:100%;height:auto"/><p><br></p>`);
    reader.readAsDataURL(file);
  }

  async function checkpoint() {
    setBusy(true);
    try {
      await save(true);
      await createStudioCheckpoint(documentId);
      setRevisions(await listStudioRevisions(documentId));
      setHistoryOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create revision checkpoint.");
    } finally {
      setBusy(false);
    }
  }

  async function openHistory() {
    try {
      setRevisions(await listStudioRevisions(documentId));
      setHistoryOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load revision history.");
    }
  }

  function restoreRevision(revision: StudioRevision) {
    if (!doc?.can_edit) return;
    setTitle(revision.title);
    setHtml(revision.html_content);
    if (editorRef.current) editorRef.current.innerHTML = revision.html_content;
    setDirty(true);
    setSaveState("unsaved");
    setHistoryOpen(false);
  }

  async function exportAs(format: "pdf" | "word") {
    setBusy(true);
    setError("");
    try {
      await save(true);
      const result = await downloadStudioDocument(documentId, format);
      saveBlobDownload(result, `guardrisk-document.${format === "word" ? "doc" : "pdf"}`);
      setExportOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to export document.");
    } finally {
      setBusy(false);
    }
  }

  async function patchMeta(patch: Partial<StudioDocument>) {
    if (!doc?.can_edit) return;
    setBusy(true);
    try {
      const updated = await saveStudioDocument(doc.id, { ...patch, expected_version: doc.version });
      setDoc(updated);
      setSaveState("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update document.");
    } finally {
      setBusy(false);
    }
  }

  if (!doc) {
    return <div className="screen-center"><div>{error || "Loading Document Studio…"}</div></div>;
  }

  const settings = doc.settings || {};
  const pageWidth = settings.page_size === "letter" ? 816 : 794;
  const pageHeight = settings.page_size === "letter" ? 1056 : 1123;
  const landscape = settings.orientation === "landscape";
  const width = landscape ? pageHeight : pageWidth;
  const minHeight = landscape ? pageWidth : pageHeight;
  const marginPx = Math.round((settings.margin_mm || 20) * 3.78);

  return (
    <div className="office-editor-shell">
      <header className="office-editor-titlebar">
        <button className="office-icon-button" onClick={() => router.push("/document-studio")} title="Back to documents">←</button>
        <div className="office-app-mark">G</div>
        <input className="office-title-input" value={title} disabled={!doc.can_edit} onChange={(e) => { setTitle(e.target.value); setDirty(true); setSaveState("unsaved"); }} />
        <div className={`office-save-state ${saveState}`}>{saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : saveState === "conflict" ? "Save conflict" : saveState === "error" ? "Save failed" : "Unsaved"}</div>
        <button className="button secondary small" onClick={() => void openHistory()}>History</button>
        <button className="button secondary small" onClick={() => void checkpoint()} disabled={!doc.can_edit || busy}>Checkpoint</button>
        <button className="button small" onClick={() => setExportOpen(true)}>Export</button>
      </header>

      {error && <div className="office-editor-error"><span>{error}</span><button onClick={() => setError("")}>×</button></div>}
      {saveState === "conflict" && <div className="office-editor-error"><span>This document changed in another session. Reload it before saving to avoid overwriting newer work.</span><button onClick={() => void load()}>Reload</button></div>}

      <div className="office-ribbon">
        <div className="office-ribbon-tabs">{(["Home", "Insert", "Layout", "Design"] as RibbonTab[]).map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
        <div className="office-ribbon-tools">
          {activeTab === "Home" && <>
            <div className="office-tool-group"><span>Clipboard</span><button onClick={() => run("undo")}>↶ Undo</button><button onClick={() => run("redo")}>↷ Redo</button></div>
            <div className="office-tool-group wide"><span>Font</span><select value={font} onChange={(e) => { setFont(e.target.value); run("fontName", e.target.value); }}>{fonts.map((item) => <option key={item}>{item}</option>)}</select><select value={fontSize} onChange={(e) => { setFontSize(e.target.value); run("fontSize", String(Math.max(1, Math.min(7, Math.round(Number(e.target.value) / 5))))); }}>{sizes.map((item) => <option key={item}>{item}</option>)}</select><button onClick={() => run("bold")}><b>B</b></button><button onClick={() => run("italic")}><i>I</i></button><button onClick={() => run("underline")}><u>U</u></button><input type="color" title="Text colour" onChange={(e) => run("foreColor", e.target.value)} /><input type="color" title="Highlight" defaultValue="#fff3a3" onChange={(e) => run("hiliteColor", e.target.value)} /></div>
            <div className="office-tool-group"><span>Paragraph</span><button onClick={() => run("insertUnorderedList")}>• List</button><button onClick={() => run("insertOrderedList")}>1. List</button><button onClick={() => run("justifyLeft")}>≡ Left</button><button onClick={() => run("justifyCenter")}>≡ Center</button><button onClick={() => run("justifyRight")}>≡ Right</button></div>
            <div className="office-tool-group"><span>Styles</span><button onClick={() => run("formatBlock", "p")}>Normal</button><button onClick={() => run("formatBlock", "h1")}>Title</button><button onClick={() => run("formatBlock", "h2")}>Heading 1</button><button onClick={() => run("formatBlock", "h3")}>Heading 2</button></div>
          </>}
          {activeTab === "Insert" && <>
            <div className="office-tool-group"><span>Pages</span><button onClick={insertPageBreak}>Page break</button><button onClick={() => insertHtml("<hr/><p><br></p>")}>Rule</button></div>
            <div className="office-tool-group"><span>Content</span><button onClick={insertTable}>Table 2×2</button><button onClick={() => imageInputRef.current?.click()}>Image</button><button onClick={insertLink}>Link</button><input ref={imageInputRef} hidden type="file" accept="image/*" onChange={(e) => chooseImage(e.target.files?.[0] || null)} /></div>
            <div className="office-tool-group wide"><span>Signature and fillable fields</span><button onClick={() => insertField("signature", "Signature")}>✍ Signature</button><button onClick={() => insertField("initials", "Initials")}>Initials</button><button onClick={() => insertField("signing_date", "Signing date")}>Date</button><button onClick={() => insertField("printed_name", "Printed name")}>Name</button><button onClick={() => insertField("title", "Title / capacity")}>Title</button><button onClick={() => insertField("text", "Text field")}>Text</button><button onClick={() => insertField("checkbox", "Consent")}>☐ Consent</button></div>
          </>}
          {activeTab === "Layout" && <>
            <div className="office-tool-group"><span>Page setup</span><label>Size<select value={settings.page_size || "a4"} onChange={(e) => void patchMeta({ settings: { ...settings, page_size: e.target.value as "a4" | "letter" } })}><option value="a4">A4</option><option value="letter">Letter</option></select></label><label>Orientation<select value={settings.orientation || "portrait"} onChange={(e) => void patchMeta({ settings: { ...settings, orientation: e.target.value as "portrait" | "landscape" } })}><option value="portrait">Portrait</option><option value="landscape">Landscape</option></select></label><label>Margins<select value={String(settings.margin_mm || 20)} onChange={(e) => void patchMeta({ settings: { ...settings, margin_mm: Number(e.target.value) } })}><option value="12">Narrow</option><option value="20">Normal</option><option value="28">Wide</option></select></label></div>
          </>}
          {activeTab === "Design" && <>
            <div className="office-tool-group wide"><span>Document themes</span>{themes.map(([key, label]) => <button key={key} className={doc.style_key === key ? "selected" : ""} onClick={() => void patchMeta({ style_key: key, settings: { ...settings, theme: key } })}>{label}</button>)}</div>
            <div className="office-tool-group"><span>Branding</span><label className="office-checkbox"><input type="checkbox" checked={settings.brand_header !== false} onChange={(e) => void patchMeta({ settings: { ...settings, brand_header: e.target.checked } })} /> Guardrisk header</label></div>
          </>}
        </div>
      </div>

      <div className="office-editor-workspace">
        <aside className="office-left-rail">
          <button className={sidePanel === "document" ? "active" : ""} onClick={() => setSidePanel(sidePanel === "document" ? "none" : "document")}>DOC</button>
          <button className={sidePanel === "fields" ? "active" : ""} onClick={() => setSidePanel(sidePanel === "fields" ? "none" : "fields")}>FLD</button>
        </aside>
        {sidePanel !== "none" && <aside className="office-side-panel">
          {sidePanel === "document" ? <>
            <h3>Document</h3><label>Status<select value={doc.status} disabled={!doc.can_edit} onChange={(e) => void patchMeta({ status: e.target.value as StudioDocument["status"] })}><option value="draft">Draft</option><option value="review">Review</option><option value="final">Final</option><option value="archived">Archived</option></select></label><label>Visibility<select value={doc.visibility} disabled={!doc.can_edit} onChange={(e) => void patchMeta({ visibility: e.target.value as StudioDocument["visibility"] })}><option value="private">Private</option><option value="team">Team</option></select></label><div className="office-info-card"><strong>Template</strong><span>{doc.template_key.replaceAll("_", " ")}</span><strong>Version</strong><span>{doc.version}</span><strong>Permission</strong><span>{doc.can_edit ? "Can edit" : "View only"}</span></div>
          </> : <><h3>Fields</h3><p>Insert signing and fillable fields from the Insert ribbon. Fields stay in the document and are included in revisions and exports.</p><div className="office-field-count"><strong>{fieldCount}</strong><span>fields in document</span></div><button onClick={() => insertField("signature", "Signature")}>+ Signature</button><button onClick={() => insertField("printed_name", "Printed name")}>+ Printed name</button><button onClick={() => insertField("signing_date", "Signing date")}>+ Signing date</button><button onClick={() => insertField("checkbox", "Consent")}>+ Consent</button></>}
        </aside>}
        <main className="office-paper-stage">
          <div className={`office-paper theme-${doc.style_key}`} style={{ width: width * zoom / 100, minHeight: minHeight * zoom / 100, padding: marginPx * zoom / 100 }}>
            {settings.brand_header !== false && <header className="office-paper-brand" contentEditable={false}><div className="office-paper-g">G</div><div><strong>GUARDRISK</strong><span>Insurance · Medical Aid · Bonds & Guarantees · Risk Management</span></div></header>}
            <div ref={editorRef} className="office-editable" contentEditable={doc.can_edit} suppressContentEditableWarning onInput={syncEditor} dangerouslySetInnerHTML={{ __html: html }} />
          </div>
        </main>
      </div>

      <footer className="office-statusbar"><span>Page size: {(settings.page_size || "a4").toUpperCase()} · {settings.orientation || "portrait"}</span><span>{words} words · {plain.length} characters · {fieldCount} fields</span><div className="office-zoom"><button onClick={() => setZoom((v) => Math.max(50, v - 10))}>−</button><input type="range" min="50" max="160" value={zoom} onChange={(e) => setZoom(Number(e.target.value))} /><span>{zoom}%</span><button onClick={() => setZoom((v) => Math.min(160, v + 10))}>+</button></div></footer>

      <SmartDialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Revision history" description="Checkpoints preserve a complete copy of the document at a specific version." size="md"><div className="office-history-list">{revisions.map((revision) => <div key={revision.id} className="office-history-item"><div><strong>Version {revision.version}</strong><span>{new Date(revision.created_at).toLocaleString()}</span><small>{revision.title}</small></div><button className="button secondary small" disabled={!doc.can_edit} onClick={() => restoreRevision(revision)}>Restore to editor</button></div>)}{!revisions.length && <div className="empty">No checkpoints yet.</div>}</div></SmartDialog>

      <SmartDialog open={exportOpen} onClose={() => setExportOpen(false)} title="Export document" description="Download the current saved workspace document or open your browser print workflow." size="sm"><div className="office-export-options"><button onClick={() => void exportAs("pdf")} disabled={busy}><strong>PDF document</strong><span>Clean server-rendered PDF for distribution.</span></button><button onClick={() => void exportAs("word")} disabled={busy}><strong>Word-compatible document</strong><span>Editable .doc file containing the rich document HTML.</span></button><button onClick={() => { window.print(); setExportOpen(false); }}><strong>Print / Save as PDF</strong><span>Print the visual editor page using your browser.</span></button></div></SmartDialog>
    </div>
  );
}
