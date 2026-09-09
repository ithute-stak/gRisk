"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { getStudioDocument, saveStudioDocument, type StudioDocument, type StudioSettings } from "@/lib/studio";

const defaults = {
  letterhead_address: "LNDC Centre, Ground Floor, Shop No. ____",
  letterhead_phone_1: "+266 2232 2537",
  letterhead_phone_2: "+266 6272 0488",
  letterhead_email: "info@guardrisk.co.ls",
  letterhead_footer_left: "GUARDRISK HEALTH",
  letterhead_footer_right: "LOW COST MEDICAL AID",
};

function normalizePhone(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const digits = trimmed.replace(/\D/g, "");
  if (digits.startsWith("266")) return `+266 ${digits.slice(3).replace(/(\d{4})(?=\d)/g, "$1 ").trim()}`;
  if (digits.startsWith("0")) return `+266 ${digits.slice(1).replace(/(\d{4})(?=\d)/g, "$1 ").trim()}`;
  return `+266 ${digits.replace(/(\d{4})(?=\d)/g, "$1 ").trim()}`;
}

function withDefaults(settings: StudioSettings = {}) {
  return { ...defaults, ...settings };
}

export default function StudioLetterheadCustomization({ documentId }: { documentId: string }) {
  const [record, setRecord] = useState<StudioDocument | null>(null);
  const [draft, setDraft] = useState(withDefaults());
  const [target, setTarget] = useState<Element | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void getStudioDocument(documentId).then((item) => {
      setRecord(item);
      setDraft(withDefaults(item.settings || {}));
    });
  }, [documentId]);

  useEffect(() => {
    const findTarget = () => setTarget(document.querySelector(".document-paper"));
    findTarget();
    const observer = new MutationObserver(findTarget);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  async function save() {
    if (!record?.can_edit) return;
    setSaving(true); setError("");
    try {
      const latest = await getStudioDocument(documentId);
      const settings = {
        ...(latest.settings || {}),
        ...draft,
        brand_header: true,
        letterhead_phone_1: normalizePhone(draft.letterhead_phone_1 || ""),
        letterhead_phone_2: normalizePhone(draft.letterhead_phone_2 || ""),
      };
      await saveStudioDocument(documentId, { settings, expected_version: latest.version });
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save letterhead details.");
      setSaving(false);
    }
  }

  const overlay = target ? createPortal(
    <div className="guardrisk-stationery-overlay" contentEditable={false}>
      <div className="guardrisk-letterhead-address"><strong>Address:</strong><span>{draft.letterhead_address}</span></div>
      <div className="guardrisk-letterhead-footer-contact">
        <span><b>⌖</b>{draft.letterhead_address}</span>
        <span><b>☎</b>{normalizePhone(draft.letterhead_phone_1 || "")} / {normalizePhone(draft.letterhead_phone_2 || "")}</span>
        <span><b>✉</b>{draft.letterhead_email}</span>
      </div>
      <div className="guardrisk-letterhead-footer-labels"><span>{draft.letterhead_footer_left}</span><span>{draft.letterhead_footer_right}</span></div>
    </div>,
    target,
  ) : null;

  return <>
    {overlay}
    <div className="studio-letterhead-customizer">
      <button className="button secondary small" onClick={() => setOpen((value) => !value)}>Letterhead details</button>
      {open && <div className="studio-letterhead-customizer-panel">
        <strong>Letterhead contacts</strong>
        <small>These details are saved with this document and used in the preview, PDF and Word export.</small>
        <label>Address<textarea value={draft.letterhead_address || ""} onChange={(e) => setDraft({ ...draft, letterhead_address: e.target.value })} placeholder="LNDC Centre, Ground Floor, Shop No. ..." /></label>
        <label>Phone 1<input value={draft.letterhead_phone_1 || ""} onChange={(e) => setDraft({ ...draft, letterhead_phone_1: e.target.value })} onBlur={() => setDraft({ ...draft, letterhead_phone_1: normalizePhone(draft.letterhead_phone_1 || "") })} /></label>
        <label>Phone 2<input value={draft.letterhead_phone_2 || ""} onChange={(e) => setDraft({ ...draft, letterhead_phone_2: e.target.value })} onBlur={() => setDraft({ ...draft, letterhead_phone_2: normalizePhone(draft.letterhead_phone_2 || "") })} /></label>
        <label>Email<input value={draft.letterhead_email || ""} onChange={(e) => setDraft({ ...draft, letterhead_email: e.target.value })} /></label>
        <label>Footer left<input value={draft.letterhead_footer_left || ""} onChange={(e) => setDraft({ ...draft, letterhead_footer_left: e.target.value })} /></label>
        <label>Footer right<input value={draft.letterhead_footer_right || ""} onChange={(e) => setDraft({ ...draft, letterhead_footer_right: e.target.value })} /></label>
        {error && <div className="office-editor-error">{error}</div>}
        <button className="button small" disabled={!record?.can_edit || saving} onClick={() => void save()}>{saving ? "Saving…" : "Save letterhead"}</button>
      </div>}
    </div>
  </>;
}
