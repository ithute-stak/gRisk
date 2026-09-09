"use client";

import { Extension, Mark, Node, mergeAttributes } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";

export type StudioFieldType = "signature" | "initials" | "date" | "name" | "title" | "text" | "checkbox";

export const STUDIO_FIELD_MIME = "application/x-grisk-document-field";

const FIELD_DEFAULTS: Record<StudioFieldType, { label: string; placeholder: string; height: number }> = {
  signature: { label: "Signature", placeholder: "Sign here", height: 62 },
  initials: { label: "Initials", placeholder: "Initial here", height: 46 },
  date: { label: "Date signed", placeholder: "DD / MM / YYYY", height: 44 },
  name: { label: "Full name", placeholder: "Type or write full name", height: 44 },
  title: { label: "Title / capacity", placeholder: "Position or capacity", height: 44 },
  text: { label: "Text field", placeholder: "Enter text", height: 48 },
  checkbox: { label: "Consent", placeholder: "Select to confirm", height: 42 },
};

function uuid() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `field-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createStudioFieldAttrs(fieldType: StudioFieldType, overrides: Record<string, unknown> = {}) {
  const defaults = FIELD_DEFAULTS[fieldType];
  return {
    fieldId: uuid(),
    fieldType,
    label: defaults.label,
    assignedTo: "Recipient",
    required: true,
    width: 100,
    height: defaults.height,
    placeholder: defaults.placeholder,
    ...overrides,
  };
}

export const PageBreak = Node.create({
  name: "pageBreak",
  group: "block",
  atom: true,
  selectable: true,
  parseHTML() {
    return [
      { tag: "div[data-page-break]" },
      { tag: ".grisk-page-break" },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-page-break": "true", class: "document-page-break" })];
  },
});

export const DocumentBlockFormatting = Extension.create({
  name: "documentBlockFormatting",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph", "heading"],
        attributes: {
          paragraphStyle: {
            default: null,
            parseHTML: (element) => element.getAttribute("data-paragraph-style"),
            renderHTML: (attributes) => attributes.paragraphStyle ? { "data-paragraph-style": attributes.paragraphStyle } : {},
          },
          lineHeight: {
            default: null,
            parseHTML: (element) => element.style.lineHeight || null,
            renderHTML: (attributes) => attributes.lineHeight ? { style: `line-height:${attributes.lineHeight}` } : {},
          },
          marginTop: {
            default: null,
            parseHTML: (element) => element.style.marginTop || null,
            renderHTML: (attributes) => attributes.marginTop ? { style: `margin-top:${attributes.marginTop}` } : {},
          },
          marginBottom: {
            default: null,
            parseHTML: (element) => element.style.marginBottom || null,
            renderHTML: (attributes) => attributes.marginBottom ? { style: `margin-bottom:${attributes.marginBottom}` } : {},
          },
          textIndent: {
            default: null,
            parseHTML: (element) => element.style.textIndent || null,
            renderHTML: (attributes) => attributes.textIndent ? { style: `text-indent:${attributes.textIndent}` } : {},
          },
          letterSpacing: {
            default: null,
            parseHTML: (element) => element.style.letterSpacing || null,
            renderHTML: (attributes) => attributes.letterSpacing ? { style: `letter-spacing:${attributes.letterSpacing}` } : {},
          },
        },
      },
    ];
  },
});

export const SubscriptMark = Mark.create({
  name: "subscript",
  excludes: "superscript",
  parseHTML() { return [{ tag: "sub" }]; },
  renderHTML({ HTMLAttributes }) { return ["sub", mergeAttributes(HTMLAttributes), 0]; },
});

export const SuperscriptMark = Mark.create({
  name: "superscript",
  excludes: "subscript",
  parseHTML() { return [{ tag: "sup" }]; },
  renderHTML({ HTMLAttributes }) { return ["sup", mergeAttributes(HTMLAttributes), 0]; },
});

function normalizeLegacyField(value: string | undefined): StudioFieldType {
  if (value === "signing_date") return "date";
  if (value === "printed_name") return "name";
  if (["signature", "initials", "date", "name", "title", "text", "checkbox"].includes(value || "")) {
    return value as StudioFieldType;
  }
  return "text";
}

function FieldNodeView({ node, selected, updateAttributes, deleteNode }: NodeViewProps) {
  const attrs = node.attrs as {
    fieldId: string;
    fieldType: StudioFieldType;
    label: string;
    assignedTo: string;
    required: boolean;
    width: number;
    height: number;
    placeholder: string;
  };

  return (
    <NodeViewWrapper
      className={`document-signature-node ${selected ? "is-selected" : ""}`}
      style={{ width: `${attrs.width}%`, minHeight: `${attrs.height}px` }}
      data-studio-field-node="true"
    >
      <div className="document-signature-drag" data-drag-handle contentEditable={false} title="Drag field">⋮⋮</div>
      <div className="document-signature-body" contentEditable={false}>
        <div className="document-signature-heading">
          <span className="document-signature-icon">{attrs.fieldType === "checkbox" ? "☐" : attrs.fieldType === "signature" ? "✍" : "▣"}</span>
          <strong>{attrs.label}</strong>
          <span className="document-signature-assignee">{attrs.assignedTo}</span>
          {attrs.required && <span className="document-signature-required-badge">Required</span>}
        </div>
        {attrs.fieldType === "checkbox" ? (
          <div className="document-signature-placeholder">☐ {attrs.placeholder}</div>
        ) : (
          <div className="document-signature-line">{attrs.placeholder}</div>
        )}
      </div>

      {selected && (
        <div className="document-signature-properties" contentEditable={false}>
          <label>
            <span>Label</span>
            <input value={attrs.label} onChange={(event) => updateAttributes({ label: event.target.value })} />
          </label>
          <label>
            <span>Assigned to</span>
            <select value={attrs.assignedTo} onChange={(event) => updateAttributes({ assignedTo: event.target.value })}>
              <option>Recipient</option>
              <option>Customer</option>
              <option>Insured</option>
              <option>Claimant</option>
              <option>Broker</option>
              <option>Guardrisk representative</option>
              <option>Witness</option>
              <option>Approver</option>
              <option>Any signer</option>
            </select>
          </label>
          <label>
            <span>Width</span>
            <select value={attrs.width} onChange={(event) => updateAttributes({ width: Number(event.target.value) })}>
              <option value={35}>Small</option>
              <option value={50}>Half</option>
              <option value={70}>Wide</option>
              <option value={100}>Full</option>
            </select>
          </label>
          <label className="document-signature-required-toggle">
            <input type="checkbox" checked={attrs.required} onChange={(event) => updateAttributes({ required: event.target.checked })} />
            Required
          </label>
          <button type="button" className="document-signature-delete" onClick={deleteNode}>Delete</button>
        </div>
      )}
    </NodeViewWrapper>
  );
}

export const StudioField = Node.create({
  name: "studioField",
  group: "block",
  atom: true,
  selectable: true,
  draggable: true,
  defining: true,

  addAttributes() {
    return {
      fieldId: { default: null },
      fieldType: { default: "signature" },
      label: { default: "Signature" },
      assignedTo: { default: "Recipient" },
      required: { default: true },
      width: { default: 100 },
      height: { default: 62 },
      placeholder: { default: "Sign here" },
    };
  },

  parseHTML() {
    return [
      {
        tag: "div[data-signature-field]",
        getAttrs: (element) => {
          const el = element as HTMLElement;
          const fieldType = normalizeLegacyField(el.dataset.fieldType);
          const defaults = FIELD_DEFAULTS[fieldType];
          return {
            fieldId: el.dataset.fieldId || uuid(),
            fieldType,
            label: el.dataset.label || defaults.label,
            assignedTo: el.dataset.assignedTo || "Recipient",
            required: el.dataset.required !== "false",
            width: Number(el.dataset.width || 100),
            height: Number(el.dataset.height || defaults.height),
            placeholder: el.dataset.placeholder || defaults.placeholder,
          };
        },
      },
      {
        tag: "span[data-grisk-field]",
        getAttrs: (element) => {
          const el = element as HTMLElement;
          const fieldType = normalizeLegacyField(el.dataset.griskField);
          const defaults = FIELD_DEFAULTS[fieldType];
          return createStudioFieldAttrs(fieldType, {
            label: el.querySelector("span")?.textContent || defaults.label,
            placeholder: defaults.placeholder,
          });
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    const fieldType = normalizeLegacyField(String(HTMLAttributes.fieldType || "signature"));
    const defaults = FIELD_DEFAULTS[fieldType];
    const label = String(HTMLAttributes.label || defaults.label);
    const assignedTo = String(HTMLAttributes.assignedTo || "Recipient");
    const required = Boolean(HTMLAttributes.required);
    const width = Number(HTMLAttributes.width || 100);
    const height = Number(HTMLAttributes.height || defaults.height);
    const placeholder = String(HTMLAttributes.placeholder || defaults.placeholder);
    return [
      "div",
      mergeAttributes({
        "data-signature-field": "true",
        "data-field-id": HTMLAttributes.fieldId,
        "data-field-type": fieldType,
        "data-label": label,
        "data-assigned-to": assignedTo,
        "data-required": required ? "true" : "false",
        "data-width": String(width),
        "data-height": String(height),
        "data-placeholder": placeholder,
        class: "document-signature-export",
        style: `width:${width}%;min-height:${height}px`,
      }),
      ["div", { class: "document-signature-export-label" }, `${label} · ${assignedTo}${required ? " · REQUIRED" : ""}`],
      ["div", { class: "document-signature-export-line" }, fieldType === "checkbox" ? `☐ ${placeholder}` : placeholder],
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(FieldNodeView);
  },
});
