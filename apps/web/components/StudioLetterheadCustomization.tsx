"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { getStudioDocument, saveStudioDocument, type StudioDocument, type StudioSettings } from "@/lib/studio";

const defaults: StudioSettings = {
  letterhead_address: "LNDC Centre, Ground Floor, Shop No. ____",
  letterhead_phone_1: "+266 2232 2537",
  letterhead_phone_2: "+266 6272 0488",
  letterhead_email: "info@guardrisk.co.ls",
  letterhead_footer_left: "GUARDRISK HEALTH",
  letterhead_footer_right: "LOW COST MEDICAL AID",
  letterhead_subject: "Your Subject Line Goes Here",
  letterhead_tagline: "YOUR LINK TO PREMIER HEALTHCARE",
  letterhead_recipient: "Recipient Name",
  letterhead_company: "Company Name",
};

function normalizePhone(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const digits = trimmed.replace(/\D/g, "");
  const local = digits.startsWith("266") ? digits.slice(3) : digits.startsWith("0") ? digits.slice(1) : digits;
  const grouped = local.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
  return grouped ? `+266 ${grouped}` : "+266";
}

function formatMaseruDateTime(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Maseru",
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.day} ${value.month} ${value.year}, ${value.hour}:${value.minute}`;
}

function documentCode(documentId?: string) {
  if (!documentId) return "GRK-00000";
  const tail = documentId.replaceAll("-", "").slice(-8);
  const numeric = Number.parseInt(tail, 16);
  return `GRK-${String(Number.isFinite(numeric) ? numeric % 100000 : 0).padStart(5, "0")}`;
}

function withDefaults(settings: StudioSettings = {}, record?: StudioDocument | null): StudioSettings {
  return {
    ...defaults,
    ...settings,
    letterhead_date_time: settings.letterhead_date_time || formatMaseruDateTime(),
    letterhead_code: settings.letterhead_code || documentCode(record?.id),
    letterhead_phone_1: normalizePhone(settings.letterhead_phone_1 || defaults.letterhead_phone_1 || ""),
    letterhead_phone_2: normalizePhone(settings.letterhead_phone_2 || defaults.letterhead_phone_2 || ""),
  };
}

export default function StudioLetterheadCustomization({ documentId }: { documentId: string }) {
  const [record, setRecord] = useState<StudioDocument | null>(null);
  const [draft, setDraft] = useState<StudioSettings>(() => withDefaults({}, null));
  const [target, setTarget] = useState<Element | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void getStudioDocument(documentId).then((item) => {
      setRecord(item);
      setDraft(withDefaults(item.settings || {}, item));
    });
  }, [documentId]);

  useEffect(() => {
    const findTarget = () => setTarget(document.querySelector(".document-paper"));
    findTarget();
    const observer = new MutationObserver(findTarget);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  function setField(key: keyof StudioSettings, value: string) {
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true);
  }

  async function save() {
    if (!record?.can_edit) return;
    setSaving(true);
    setError("");
    try {
      // Ask the rich-text editor to flush any pending body edits before the
      // settings write so its optimistic version stays in sync.
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true }));
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      const latest = await getStudioDocument(documentId);
      const settings: StudioSettings = {
        ...(latest.settings || {}),
        ...draft,
        brand_header: true,
        letterhead_phone_1: normalizePhone(draft.letterhead_phone_1 || ""),
        letterhead_phone_2: normalizePhone(draft.letterhead_phone_2 || ""),
      };
      await saveStudioDocument(documentId, { settings, expected_version: latest.version });
      setDirty(false);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save template fields.");
      setSaving(false);
    }
  }

  const editable = Boolean(record?.can_edit);
  const overlay = target ? createPortal(
    <div className="guardrisk-stationery-overlay" contentEditable={false}>
      <div className="guardrisk-brand-lockup" aria-hidden="true">
        <div className="guardrisk-brand-g">G</div>
        <div className="guardrisk-brand-name">GUARDRISK</div>
      </div>

      <input
        className="guardrisk-tagline-input"
        aria-label="Letterhead tagline"
        disabled={!editable}
        value={draft.letterhead_tagline || ""}
        onChange={(event) => setField("letterhead_tagline", event.target.value)}
      />

      <div className="guardrisk-letter-meta">
        <label><b>Date:</b><input disabled={!editable} value={draft.letterhead_date_time || ""} onChange={(event) => setField("letterhead_date_time", event.target.value)} /></label>
        <label><b>Code:</b><input disabled={!editable} value={draft.letterhead_code || ""} onChange={(event) => setField("letterhead_code", event.target.value)} /></label>
        <label><b>To:</b><input disabled={!editable} value={draft.letterhead_recipient || ""} onChange={(event) => setField("letterhead_recipient", event.target.value)} /></label>
        <label><b>Company:</b><input disabled={!editable} value={draft.letterhead_company || ""} onChange={(event) => setField("letterhead_company", event.target.value)} /></label>
      </div>

      <label className="guardrisk-letterhead-address">
        <strong>Address:</strong>
        <textarea disabled={!editable} value={draft.letterhead_address || ""} onChange={(event) => setField("letterhead_address", event.target.value)} />
      </label>

      <label className="guardrisk-subject-line">
        <b>RE:</b>
        <input disabled={!editable} value={draft.letterhead_subject || ""} onChange={(event) => setField("letterhead_subject", event.target.value)} />
      </label>

      <div className="guardrisk-letterhead-footer-contact">
        <label><b>⌖</b><textarea disabled={!editable} value={draft.letterhead_address || ""} onChange={(event) => setField("letterhead_address", event.target.value)} /></label>
        <label><b>☎</b><span><input disabled={!editable} value={draft.letterhead_phone_1 || ""} onChange={(event) => setField("letterhead_phone_1", event.target.value)} onBlur={() => setField("letterhead_phone_1", normalizePhone(draft.letterhead_phone_1 || ""))} /><input disabled={!editable} value={draft.letterhead_phone_2 || ""} onChange={(event) => setField("letterhead_phone_2", event.target.value)} onBlur={() => setField("letterhead_phone_2", normalizePhone(draft.letterhead_phone_2 || ""))} /></span></label>
        <label><b>✉</b><input disabled={!editable} value={draft.letterhead_email || ""} onChange={(event) => setField("letterhead_email", event.target.value)} /></label>
      </div>

      <div className="guardrisk-letterhead-footer-labels">
        <input disabled={!editable} value={draft.letterhead_footer_left || ""} onChange={(event) => setField("letterhead_footer_left", event.target.value)} />
        <input disabled={!editable} value={draft.letterhead_footer_right || ""} onChange={(event) => setField("letterhead_footer_right", event.target.value)} />
      </div>
    </div>,
    target,
  ) : null;

  return <>
    {overlay}
    <div className="studio-letterhead-customizer">
      <div className="studio-letterhead-customizer-actions">
        <button className="button secondary small" onClick={() => setOpen((value) => !value)}>Template fields</button>
        {dirty && <button className="button small" disabled={!editable || saving} onClick={() => void save()}>{saving ? "Saving…" : "Save fields"}</button>}
      </div>
      {open && <div className="studio-letterhead-customizer-panel">
        <strong>Editable letter template</strong>
        <small>Every field below is saved with this document and used in the editor preview, PDF and Word export. Phone numbers are normalized to +266.</small>
        <label>Date & time<input value={draft.letterhead_date_time || ""} onChange={(event) => setField("letterhead_date_time", event.target.value)} /></label>
        <label>Code<input value={draft.letterhead_code || ""} onChange={(event) => setField("letterhead_code", event.target.value)} /></label>
        <label>Recipient<input value={draft.letterhead_recipient || ""} onChange={(event) => setField("letterhead_recipient", event.target.value)} /></label>
        <label>Company<input value={draft.letterhead_company || ""} onChange={(event) => setField("letterhead_company", event.target.value)} /></label>
        <label>Address<textarea value={draft.letterhead_address || ""} onChange={(event) => setField("letterhead_address", event.target.value)} placeholder="LNDC Centre, Ground Floor, Shop No. ..." /></label>
        <label>Tagline<input value={draft.letterhead_tagline || ""} onChange={(event) => setField("letterhead_tagline", event.target.value)} /></label>
        <label>Subject<input value={draft.letterhead_subject || ""} onChange={(event) => setField("letterhead_subject", event.target.value)} /></label>
        <label>Phone 1<input value={draft.letterhead_phone_1 || ""} onChange={(event) => setField("letterhead_phone_1", event.target.value)} onBlur={() => setField("letterhead_phone_1", normalizePhone(draft.letterhead_phone_1 || ""))} /></label>
        <label>Phone 2<input value={draft.letterhead_phone_2 || ""} onChange={(event) => setField("letterhead_phone_2", event.target.value)} onBlur={() => setField("letterhead_phone_2", normalizePhone(draft.letterhead_phone_2 || ""))} /></label>
        <label>Email<input value={draft.letterhead_email || ""} onChange={(event) => setField("letterhead_email", event.target.value)} /></label>
        <label>Footer left<input value={draft.letterhead_footer_left || ""} onChange={(event) => setField("letterhead_footer_left", event.target.value)} /></label>
        <label>Footer right<input value={draft.letterhead_footer_right || ""} onChange={(event) => setField("letterhead_footer_right", event.target.value)} /></label>
        {error && <div className="office-editor-error">{error}</div>}
        <button className="button small" disabled={!editable || saving || !dirty} onClick={() => void save()}>{saving ? "Saving…" : "Save template fields"}</button>
      </div>}
    </div>
  </>;
}
