"use client";

import { Color, FontFamily, FontSize, TextStyle } from "@tiptap/extension-text-style";
import Highlight from "@tiptap/extension-highlight";
import Image from "@tiptap/extension-image";
import Placeholder from "@tiptap/extension-placeholder";
import { TableKit } from "@tiptap/extension-table";
import TextAlign from "@tiptap/extension-text-align";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { SmartDialog } from "@/components/SmartUi";
import {
  DocumentBlockFormatting,
  PageBreak,
  STUDIO_FIELD_MIME,
  StudioField,
  SubscriptMark,
  SuperscriptMark,
  createStudioFieldAttrs,
  type StudioFieldType,
} from "@/components/document-studio/DocumentEditorExtensions";
import {
  createStudioCheckpoint,
  downloadStudioDocument,
  getStudioDocument,
  listStudioRevisions,
  saveBlobDownload,
  saveStudioDocument,
  type StudioDocument,
  type StudioRevision,
  type StudioSettings,
} from "@/lib/studio";

type RibbonTab = "Home" | "Insert" | "Layout" | "Design";
type SaveState = "loading" | "saved" | "saving" | "unsaved" | "conflict" | "error";
type SidePanel = "none" | "document" | "fields";

const extensions = [
  StarterKit.configure({ link: { openOnClick: false, autolink: true, defaultProtocol: "https" } }),
  TextStyle,
  FontSize,
  FontFamily,
  Color,
  Highlight.configure({ multicolor: true }),
  TextAlign.configure({ types: ["heading", "paragraph"] }),
  Image.configure({ allowBase64: true, inline: false }),
  Placeholder.configure({ placeholder: "Start writing your document…" }),
  TableKit.configure({ table: { resizable: true } }),
  DocumentBlockFormatting,
  SubscriptMark,
  SuperscriptMark,
  StudioField,
  PageBreak,
];

const FONTS = ["Arial", "Aptos", "Calibri", "Cambria", "Georgia", "Helvetica", "Times New Roman", "Trebuchet MS", "Verdana", "Courier New"];
const FONT_SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72];

const THEMES = [
  ["guardrisk_orange", "Guardrisk Orange"],
  ["classic_word", "Classic Word"],
  ["executive_charcoal", "Executive Charcoal"],
  ["elegant", "Elegant"],
  ["legal_monochrome", "Legal Monochrome"],
  ["warm_professional", "Warm Professional"],
  ["minimal_clean", "Minimal Clean"],
] as const;

const FIELD_TYPES: Array<{ type: StudioFieldType; label: string; short: string }> = [
  { type: "signature", label: "Signature", short: "✍ Signature" },
  { type: "initials", label: "Initials", short: "Initials" },
  { type: "date", label: "Date signed", short: "Date" },
  { type: "name", label: "Full name", short: "Name" },
  { type: "title", label: "Title / capacity", short: "Title" },
  { type: "text", label: "Text field", short: "Text" },
  { type: "checkbox", label: "Consent", short: "☐ Consent" },
];

const WORD_STYLES = [
  ["normal", "Normal"],
  ["no_spacing", "No Spacing"],
  ["title", "Title"],
  ["subtitle", "Subtitle"],
  ["heading_1", "Heading 1"],
  ["heading_2", "Heading 2"],
  ["heading_3", "Heading 3"],
  ["quote", "Quote"],
  ["intense_quote", "Intense Quote"],
] as const;

function textFromHtml(html: string) {
  if (typeof document === "undefined") return "";
  const node = document.createElement("div");
  node.innerHTML = html;
  node.querySelectorAll("[data-signature-field]").forEach((field) => {
    const label = field.getAttribute("data-label") || "Field";
    field.replaceWith(document.createTextNode(`[${label}]`));
  });
  return (node.textContent || "").replace(/\s+/g, " ").trim();
}

function hasStructuredContent(value: Record<string, unknown> | null | undefined) {
  return Boolean(value && value.type === "doc" && Array.isArray(value.content) && value.content.length);
}

function defaultSettings(settings: StudioSettings): Required<Pick<StudioSettings,
  "page_size" | "orientation" | "margin_top_mm" | "margin_right_mm" | "margin_bottom_mm" | "margin_left_mm" | "brand_header" | "default_font_family" | "default_font_size_pt" | "default_line_height_percent"
>> & StudioSettings {
  const fallbackMargin = settings.margin_mm ?? 20;
  return {
    ...settings,
    page_size: settings.page_size ?? "a4",
    orientation: settings.orientation ?? "portrait",
    margin_top_mm: settings.margin_top_mm ?? fallbackMargin,
    margin_right_mm: settings.margin_right_mm ?? fallbackMargin,
    margin_bottom_mm: settings.margin_bottom_mm ?? fallbackMargin,
    margin_left_mm: settings.margin_left_mm ?? fallbackMargin,
    brand_header: settings.brand_header !== false,
    default_font_family: settings.default_font_family ?? "Arial",
    default_font_size_pt: settings.default_font_size_pt ?? 11,
    default_line_height_percent: settings.default_line_height_percent ?? 115,
  };
}

function applyWordStyle(editor: Editor, styleKey: string) {
  const block = {
    paragraphStyle: styleKey,
    lineHeight: null,
    marginTop: null,
    marginBottom: null,
    textIndent: null,
    letterSpacing: null,
  };
  const chain = editor.chain().focus().unsetAllMarks();
  if (styleKey === "title") {
    chain.setHeading({ level: 1 }).updateAttributes("heading", { ...block, lineHeight: "1.1", marginBottom: "12pt" }).setFontFamily("Arial").setFontSize("30pt").setColor("#3d2a1d").setTextAlign("center").run();
    return;
  }
  if (styleKey === "subtitle") {
    chain.setParagraph().updateAttributes("paragraph", { ...block, lineHeight: "1.25", marginBottom: "14pt" }).setFontSize("14pt").setColor("#6b7280").setTextAlign("center").run();
    return;
  }
  if (["heading_1", "heading_2", "heading_3"].includes(styleKey)) {
    const level = Number(styleKey.slice(-1)) as 1 | 2 | 3;
    const size = ({ 1: "20pt", 2: "15pt", 3: "12pt" } as const)[level];
    chain.setHeading({ level }).updateAttributes("heading", { ...block, lineHeight: "1.2", marginTop: level === 1 ? "16pt" : "12pt", marginBottom: "7pt" }).setFontFamily("Arial").setFontSize(size).setColor("#3d2a1d").setTextAlign("left").run();
    return;
  }
  if (styleKey === "quote" || styleKey === "intense_quote") {
    chain.setParagraph().toggleBlockquote().setFontFamily("Georgia").setFontSize(styleKey === "intense_quote" ? "12pt" : "11pt").setColor(styleKey === "intense_quote" ? "#d95f0b" : "#475569").run();
    return;
  }
  if (styleKey === "no_spacing") {
    chain.setParagraph().updateAttributes("paragraph", { ...block, lineHeight: "1", marginTop: "0", marginBottom: "0" }).setFontFamily("Arial").setFontSize("11pt").setColor("#25272b").setTextAlign("left").run();
    return;
  }
  chain.setParagraph().updateAttributes("paragraph", { ...block, lineHeight: "1.15", marginTop: "0", marginBottom: "8pt" }).setFontFamily("Arial").setFontSize("11pt").setColor("#25272b").setTextAlign("left").run();
}

export default function LoanHubDocumentStudioEditor({ documentId }: { documentId: string }) {
  const router = useRouter();
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const saveTimer = useRef<number | null>(null);
  const versionRef = useRef(1);
  const titleRef = useRef("");
  const initializedRef = useRef(false);
  const canEditRef = useRef(false);
  const savingRef = useRef(false);
  const queuedSaveRef = useRef(false);

  const [record, setRecord] = useState<StudioDocument | null>(null);
  const [title, setTitle] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("loading");
  const [activeTab, setActiveTab] = useState<RibbonTab>("Home");
  const [sidePanel, setSidePanel] = useState<SidePanel>("document");
  const [zoom, setZoom] = useState(90);
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [revisions, setRevisions] = useState<StudioRevision[]>([]);
  const [exportOpen, setExportOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const editor = useEditor({
    extensions,
    content: "",
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "office-editable document-editor-content",
        spellcheck: "true",
        "aria-label": "Document body editor",
      },
    },
    onUpdate: () => scheduleAutosave(),
  });

  const load = useCallback(async () => {
    initializedRef.current = false;
    setSaveState("loading");
    setError("");
    try {
      const item = await getStudioDocument(documentId);
      setRecord(item);
      setTitle(item.title);
      titleRef.current = item.title;
      versionRef.current = item.version;
      canEditRef.current = item.can_edit;
      setSaveState("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load document.");
      setSaveState("error");
    }
  }, [documentId]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (!editor || !record || initializedRef.current) return;
    const content = hasStructuredContent(record.content_json) ? record.content_json : record.html_content || "<p></p>";
    queueMicrotask(() => {
      if (editor.isDestroyed || initializedRef.current) return;
      editor.commands.setContent(content as never, { emitUpdate: false });
      editor.setEditable(record.can_edit);
      initializedRef.current = true;
    });
  }, [editor, record]);

  useEffect(() => () => {
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
  }, []);

  const save = useCallback(async (manual = false): Promise<boolean> => {
    if (!editor || !record?.can_edit) return true;
    if (!manual && saveState === "saved") return true;
    if (saveTimer.current) {
      window.clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
    if (savingRef.current) {
      queuedSaveRef.current = true;
      return false;
    }
    savingRef.current = true;
    setSaveState("saving");
    try {
      const htmlContent = editor.getHTML();
      const updated = await saveStudioDocument(documentId, {
        title: titleRef.current.trim() || "Untitled document",
        content_json: editor.getJSON() as Record<string, unknown>,
        html_content: htmlContent,
        plain_text: textFromHtml(htmlContent),
        expected_version: versionRef.current,
      });
      versionRef.current = updated.version;
      setRecord(updated);
      setSaveState("saved");
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save document.";
      setError(message);
      setSaveState(message.toLowerCase().includes("changed elsewhere") ? "conflict" : "error");
      return false;
    } finally {
      savingRef.current = false;
      if (queuedSaveRef.current) {
        queuedSaveRef.current = false;
        window.setTimeout(() => void save(false), 0);
      }
    }
  }, [documentId, editor, record?.can_edit, saveState]);

  function scheduleAutosave() {
    if (!canEditRef.current || !initializedRef.current) return;
    setSaveState("unsaved");
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => void save(false), 1000);
  }

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

  const statistics = useMemo(() => {
    if (!editor) return { words: 0, characters: 0, fields: 0 };
    const text = editor.getText({ blockSeparator: "\n" });
    let fields = 0;
    editor.state.doc.descendants((node) => { if (node.type.name === "studioField") fields += 1; });
    return { words: text.trim() ? text.trim().split(/\s+/).length : 0, characters: text.length, fields };
  }, [editor, saveState, record?.version]);

  async function patchDocument(patch: Partial<StudioDocument>) {
    if (!record?.can_edit || !editor) return;
    const saved = await save(false);
    if (!saved && saveState === "conflict") return;
    setBusy(true);
    try {
      const updated = await saveStudioDocument(documentId, { ...patch, expected_version: versionRef.current });
      versionRef.current = updated.version;
      setRecord(updated);
      setSaveState("saved");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to update document settings.";
      setError(message);
      if (message.toLowerCase().includes("changed elsewhere")) setSaveState("conflict");
    } finally {
      setBusy(false);
    }
  }

  async function patchSettings(patch: Partial<StudioSettings>) {
    if (!record) return;
    await patchDocument({ settings: { ...defaultSettings(record.settings || {}), ...patch } });
  }

  function insertField(type: StudioFieldType) {
    if (!editor || !record?.can_edit) return;
    editor.chain().focus().insertContent({ type: "studioField", attrs: createStudioFieldAttrs(type) }).run();
  }

  function fieldDragStart(event: React.DragEvent<HTMLButtonElement>, type: StudioFieldType) {
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData(STUDIO_FIELD_MIME, JSON.stringify(createStudioFieldAttrs(type)));
  }

  function handlePaperDrop(event: React.DragEvent<HTMLDivElement>) {
    if (!editor || !record?.can_edit) return;
    const raw = event.dataTransfer.getData(STUDIO_FIELD_MIME);
    if (!raw) return;
    event.preventDefault();
    event.stopPropagation();
    try {
      const attrs = JSON.parse(raw) as Record<string, unknown>;
      const position = editor.view.posAtCoords({ left: event.clientX, top: event.clientY });
      editor.chain().focus().insertContentAt(position?.pos ?? editor.state.selection.anchor, { type: "studioField", attrs }).run();
    } catch {
      setError("The field could not be added.");
    }
  }

  function insertLink() {
    if (!editor || !record?.can_edit) return;
    const previous = editor.getAttributes("link").href as string | undefined;
    const value = window.prompt("Enter the link URL", previous || "https://");
    if (value === null) return;
    if (!value.trim()) editor.chain().focus().unsetLink().run();
    else editor.chain().focus().extendMarkRange("link").setLink({ href: value.trim() }).run();
  }

  function imageSelected(file: File | undefined) {
    if (!editor || !file || !record?.can_edit) return;
    if (!file.type.startsWith("image/")) { setError("Choose an image file."); return; }
    if (file.size > 2 * 1024 * 1024) { setError("Document images must be smaller than 2 MB."); return; }
    const reader = new FileReader();
    reader.onload = () => editor.chain().focus().setImage({ src: String(reader.result), alt: file.name }).run();
    reader.readAsDataURL(file);
  }

  async function openHistory() {
    try {
      setRevisions(await listStudioRevisions(documentId));
      setHistoryOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load revision history.");
    }
  }

  async function checkpoint() {
    if (!(await save(true))) return;
    setBusy(true);
    try {
      await createStudioCheckpoint(documentId);
      setRevisions(await listStudioRevisions(documentId));
      setHistoryOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create revision checkpoint.");
    } finally {
      setBusy(false);
    }
  }

  function restoreRevision(revision: StudioRevision) {
    if (!editor || !record?.can_edit) return;
    titleRef.current = revision.title;
    setTitle(revision.title);
    const content = hasStructuredContent(revision.content_json) ? revision.content_json : revision.html_content;
    editor.commands.setContent(content as never, { emitUpdate: false });
    setHistoryOpen(false);
    setSaveState("unsaved");
    scheduleAutosave();
  }

  async function exportAs(format: "pdf" | "docx") {
    if (!(await save(true))) return;
    setBusy(true);
    setError("");
    try {
      const result = await downloadStudioDocument(documentId, format);
      saveBlobDownload(result, `guardrisk-document.${format}`);
      setExportOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to export document.");
    } finally {
      setBusy(false);
    }
  }

  if (!editor || !record || saveState === "loading") {
    return <div className="screen-center"><div>{error || "Loading Document Studio…"}</div></div>;
  }

  const settings = defaultSettings(record.settings || {});
  const baseWidth = settings.page_size === "letter" ? 215.9 : 210;
  const baseHeight = settings.page_size === "letter" ? 279.4 : 297;
  const widthMm = settings.orientation === "landscape" ? baseHeight : baseWidth;
  const heightMm = settings.orientation === "landscape" ? baseWidth : baseHeight;

  return (
    <div className="office-editor-shell loanhub-studio-engine">
      <header className="office-editor-titlebar">
        <button className="office-icon-button" onClick={() => router.push("/document-studio")} title="Back to documents">←</button>
        <div className="office-app-mark">G</div>
        <input
          className="office-title-input"
          value={title}
          disabled={!record.can_edit}
          onChange={(event) => {
            setTitle(event.target.value);
            titleRef.current = event.target.value;
            scheduleAutosave();
          }}
        />
        <div className={`office-save-state ${saveState}`}>{saveState === "saving" ? "Saving…" : saveState === "saved" ? `Saved · v${versionRef.current}` : saveState === "conflict" ? "Save conflict" : saveState === "error" ? "Save failed" : "Unsaved"}</div>
        <button className="button secondary small" onClick={() => void openHistory()}>History</button>
        <button className="button secondary small" onClick={() => void checkpoint()} disabled={!record.can_edit || busy}>Save checkpoint</button>
        <button className="button small" onClick={() => setExportOpen(true)}>Export</button>
      </header>

      {error && <div className="office-editor-error"><span>{error}</span><button onClick={() => setError("")}>×</button></div>}
      {saveState === "conflict" && <div className="office-editor-error"><span>This document changed in another session. Reload before saving so newer work is not overwritten.</span><button onClick={() => void load()}>Reload</button></div>}

      <section className="office-ribbon loanhub-document-ribbon">
        <div className="office-ribbon-tabs">{(["Home", "Insert", "Layout", "Design"] as RibbonTab[]).map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
        <div className="office-ribbon-tools">
          {activeTab === "Home" && <>
            <div className="office-tool-group"><span>History</span><button disabled={!record.can_edit} onClick={() => editor.chain().focus().undo().run()}>↶ Undo</button><button disabled={!record.can_edit} onClick={() => editor.chain().focus().redo().run()}>↷ Redo</button></div>
            <div className="office-tool-group wide"><span>Font</span>
              <select disabled={!record.can_edit} value={String(editor.getAttributes("textStyle").fontFamily || settings.default_font_family)} onChange={(e) => editor.chain().focus().setFontFamily(e.target.value).run()}>{FONTS.map((font) => <option key={font}>{font}</option>)}</select>
              <select disabled={!record.can_edit} value={String(editor.getAttributes("textStyle").fontSize || `${settings.default_font_size_pt}pt`)} onChange={(e) => editor.chain().focus().setFontSize(e.target.value).run()}>{FONT_SIZES.map((size) => <option key={size} value={`${size}pt`}>{size}</option>)}</select>
              <button className={editor.isActive("bold") ? "selected" : ""} onClick={() => editor.chain().focus().toggleBold().run()}><b>B</b></button>
              <button className={editor.isActive("italic") ? "selected" : ""} onClick={() => editor.chain().focus().toggleItalic().run()}><i>I</i></button>
              <button className={editor.isActive("underline") ? "selected" : ""} onClick={() => editor.chain().focus().toggleUnderline().run()}><u>U</u></button>
              <button className={editor.isActive("subscript") ? "selected" : ""} onClick={() => editor.chain().focus().toggleMark("subscript").run()}>x₂</button>
              <button className={editor.isActive("superscript") ? "selected" : ""} onClick={() => editor.chain().focus().toggleMark("superscript").run()}>x²</button>
              <input type="color" title="Text colour" defaultValue="#25272b" onChange={(e) => editor.chain().focus().setColor(e.target.value).run()} />
              <input type="color" title="Highlight" defaultValue="#fff1a8" onChange={(e) => editor.chain().focus().toggleHighlight({ color: e.target.value }).run()} />
            </div>
            <div className="office-tool-group"><span>Paragraph</span>
              <button onClick={() => editor.chain().focus().toggleBulletList().run()}>• List</button><button onClick={() => editor.chain().focus().toggleOrderedList().run()}>1. List</button>
              <button onClick={() => editor.chain().focus().setTextAlign("left").run()}>Left</button><button onClick={() => editor.chain().focus().setTextAlign("center").run()}>Center</button><button onClick={() => editor.chain().focus().setTextAlign("right").run()}>Right</button><button onClick={() => editor.chain().focus().setTextAlign("justify").run()}>Justify</button>
              <select title="Line spacing" value={String(editor.getAttributes(editor.isActive("heading") ? "heading" : "paragraph").lineHeight || "1.15")} onChange={(e) => editor.chain().focus().updateAttributes(editor.isActive("heading") ? "heading" : "paragraph", { lineHeight: e.target.value }).run()}><option value="1">1.0</option><option value="1.15">1.15</option><option value="1.5">1.5</option><option value="2">2.0</option></select>
            </div>
            <div className="office-tool-group office-style-gallery"><span>Styles</span>{WORD_STYLES.map(([key, label]) => <button key={key} onClick={() => applyWordStyle(editor, key)}>{label}</button>)}</div>
          </>}

          {activeTab === "Insert" && <>
            <div className="office-tool-group"><span>Pages</span><button onClick={() => editor.chain().focus().insertContent({ type: "pageBreak" }).run()}>Page break</button><button onClick={() => editor.chain().focus().setHorizontalRule().run()}>Rule</button></div>
            <div className="office-tool-group"><span>Content</span><button onClick={() => editor.chain().focus().insertTable({ rows: 2, cols: 2, withHeaderRow: true }).run()}>Table 2×2</button><button onClick={() => imageInputRef.current?.click()}>Image</button><button onClick={insertLink}>Link</button><input ref={imageInputRef} hidden type="file" accept="image/*" onChange={(e) => imageSelected(e.target.files?.[0])} /></div>
            {editor.isActive("table") && <div className="office-tool-group"><span>Table</span><button onClick={() => editor.chain().focus().addRowAfter().run()}>+ Row</button><button onClick={() => editor.chain().focus().addColumnAfter().run()}>+ Column</button><button onClick={() => editor.chain().focus().deleteRow().run()}>− Row</button><button onClick={() => editor.chain().focus().deleteColumn().run()}>− Column</button><button onClick={() => editor.chain().focus().deleteTable().run()}>Delete table</button></div>}
            <div className="office-tool-group wide"><span>Signature and fillable fields</span>{FIELD_TYPES.map((field) => <button key={field.type} draggable onDragStart={(event) => fieldDragStart(event, field.type)} onClick={() => insertField(field.type)}>{field.short}</button>)}</div>
          </>}

          {activeTab === "Layout" && <>
            <div className="office-tool-group"><span>Page setup</span><label>Size<select value={settings.page_size} onChange={(e) => void patchSettings({ page_size: e.target.value as "a4" | "letter" })}><option value="a4">A4</option><option value="letter">Letter</option></select></label><label>Orientation<select value={settings.orientation} onChange={(e) => void patchSettings({ orientation: e.target.value as "portrait" | "landscape" })}><option value="portrait">Portrait</option><option value="landscape">Landscape</option></select></label></div>
            <div className="office-tool-group"><span>Margins</span><button onClick={() => void patchSettings({ margin_top_mm: 12, margin_right_mm: 12, margin_bottom_mm: 12, margin_left_mm: 12 })}>Narrow</button><button onClick={() => void patchSettings({ margin_top_mm: 20, margin_right_mm: 20, margin_bottom_mm: 20, margin_left_mm: 20 })}>Normal</button><button onClick={() => void patchSettings({ margin_top_mm: 28, margin_right_mm: 28, margin_bottom_mm: 28, margin_left_mm: 28 })}>Wide</button></div>
            <div className="office-tool-group"><span>Defaults</span><label>Font<select value={settings.default_font_family} onChange={(e) => void patchSettings({ default_font_family: e.target.value })}>{FONTS.map((font) => <option key={font}>{font}</option>)}</select></label><label>Size<select value={settings.default_font_size_pt} onChange={(e) => void patchSettings({ default_font_size_pt: Number(e.target.value) })}>{FONT_SIZES.filter((size) => size <= 36).map((size) => <option key={size}>{size}</option>)}</select></label></div>
          </>}

          {activeTab === "Design" && <>
            <div className="office-tool-group wide"><span>Document themes</span>{THEMES.map(([key, label]) => <button key={key} className={record.style_key === key ? "selected" : ""} onClick={() => void patchDocument({ style_key: key, settings: { ...settings, theme: key } })}>{label}</button>)}</div>
            <div className="office-tool-group"><span>Branding</span><label className="office-checkbox"><input type="checkbox" checked={settings.brand_header} onChange={(e) => void patchSettings({ brand_header: e.target.checked })} /> Guardrisk header</label></div>
          </>}
        </div>
      </section>

      <div className="office-editor-workspace">
        <aside className="office-left-rail"><button className={sidePanel === "document" ? "active" : ""} onClick={() => setSidePanel(sidePanel === "document" ? "none" : "document")}>DOC</button><button className={sidePanel === "fields" ? "active" : ""} onClick={() => setSidePanel(sidePanel === "fields" ? "none" : "fields")}>FLD</button></aside>
        {sidePanel !== "none" && <aside className="office-side-panel">
          {sidePanel === "document" ? <>
            <h3>Document</h3>
            <label>Status<select value={record.status} disabled={!record.can_edit} onChange={(e) => void patchDocument({ status: e.target.value as StudioDocument["status"] })}><option value="draft">Draft</option><option value="review">Review</option><option value="final">Final</option><option value="archived">Archived</option></select></label>
            <label>Visibility<select value={record.visibility} disabled={!record.can_edit} onChange={(e) => void patchDocument({ visibility: e.target.value as StudioDocument["visibility"] })}><option value="private">Private</option><option value="team">Team</option></select></label>
            <div className="office-info-card"><strong>Template</strong><span>{record.template_key.replaceAll("_", " ")}</span><strong>Version</strong><span>{versionRef.current}</span><strong>Permission</strong><span>{record.can_edit ? "Can edit" : "View only"}</span></div>
            <p>Structured TipTap content is saved with the document, so formatting, tables and fields survive revisions and export.</p>
          </> : <>
            <h3>Fields</h3><p>Click a field to insert it, or drag it onto the exact document position. Select a field in the document to edit its label, signer, width and required state.</p>
            <div className="office-field-count"><strong>{statistics.fields}</strong><span>fields in document</span></div>
            <div className="studio-field-palette">{FIELD_TYPES.map((field) => <button key={field.type} draggable onDragStart={(event) => fieldDragStart(event, field.type)} onClick={() => insertField(field.type)}><b>{field.short}</b><small>Drag or click to add</small></button>)}</div>
          </>}
        </aside>}

        <main className="office-paper-stage">
          <div className="document-paper-transform" style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top center" }}>
            <div
              className={`office-paper document-paper theme-${record.style_key}`}
              style={{ width: `${widthMm}mm`, minHeight: `${heightMm}mm`, padding: `${settings.margin_top_mm}mm ${settings.margin_right_mm}mm ${settings.margin_bottom_mm}mm ${settings.margin_left_mm}mm`, fontFamily: settings.default_font_family, fontSize: `${settings.default_font_size_pt}pt`, lineHeight: settings.default_line_height_percent / 100 }}
              onDragOver={(event) => { if (event.dataTransfer.types.includes(STUDIO_FIELD_MIME)) { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; } }}
              onDrop={handlePaperDrop}
            >
              {settings.brand_header && <header className="office-paper-brand" contentEditable={false}><div className="office-paper-g">G</div><div><strong>GUARDRISK</strong><span>Insurance · Medical Aid · Bonds & Guarantees · Risk Management</span></div></header>}
              <EditorContent editor={editor} />
            </div>
          </div>
        </main>
      </div>

      <footer className="office-statusbar"><span>{settings.page_size.toUpperCase()} · {settings.orientation}</span><span>{statistics.words} words · {statistics.characters} characters · {statistics.fields} fields</span><div className="office-zoom"><button onClick={() => setZoom((value) => Math.max(50, value - 10))}>−</button><input type="range" min="50" max="140" step="5" value={zoom} onChange={(e) => setZoom(Number(e.target.value))} /><span>{zoom}%</span><button onClick={() => setZoom((value) => Math.min(140, value + 10))}>+</button></div></footer>

      <SmartDialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Revision history" description="Checkpoints preserve the structured editor document, rich HTML and page settings." size="md"><div className="office-history-list">{revisions.map((revision) => <div key={revision.id} className="office-history-item"><div><strong>Version {revision.version}</strong><span>{new Date(revision.created_at).toLocaleString()}</span><small>{revision.title}</small></div><button className="button secondary small" disabled={!record.can_edit} onClick={() => restoreRevision(revision)}>Restore to editor</button></div>)}{!revisions.length && <div className="empty">No checkpoints yet.</div>}</div></SmartDialog>

      <SmartDialog open={exportOpen} onClose={() => setExportOpen(false)} title="Export document" description="Export the saved document with its formatting, tables and signing fields." size="sm"><div className="office-export-options"><button onClick={() => void exportAs("pdf")} disabled={busy}><strong>PDF document</strong><span>Server-rendered distribution copy.</span></button><button onClick={() => void exportAs("docx")} disabled={busy}><strong>Microsoft Word (.docx)</strong><span>Real editable OOXML Word document.</span></button><button onClick={() => { window.print(); setExportOpen(false); }}><strong>Print</strong><span>Open the browser print workflow for the visual document.</span></button></div></SmartDialog>
    </div>
  );
}
