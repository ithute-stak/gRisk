"use client";

import { apiDownload, apiGet, apiPatch, apiPost, apiRequest } from "@/lib/api";

export type StudioSettings = {
  page_size?: "a4" | "letter";
  orientation?: "portrait" | "landscape";
  margin_mm?: number;
  theme?: string;
  brand_header?: boolean;
};

export type StudioDocument = {
  id: string;
  owner_user_id: string;
  title: string;
  template_key: string;
  style_key: string;
  status: "draft" | "review" | "final" | "archived";
  visibility: "private" | "team";
  html_content: string;
  plain_text: string;
  settings: StudioSettings;
  version: number;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
};

export type StudioRevision = {
  id: string;
  version: number;
  title: string;
  html_content: string;
  plain_text: string;
  settings: StudioSettings;
  created_at: string;
};

export type StudioCollaborator = {
  user_id: string;
  name: string;
  email: string;
  permission: "view" | "edit";
};

export async function listStudioDocuments(q = "", status = "") {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (status) params.set("document_status", status);
  const suffix = params.toString() ? `?${params}` : "";
  return apiGet<StudioDocument[]>(`/api/v1/document-studio/documents${suffix}`);
}

export function createStudioDocument(payload: {
  title: string;
  template_key: string;
  style_key: string;
  html_content: string;
  plain_text: string;
  settings: StudioSettings;
  visibility?: "private" | "team";
}) {
  return apiPost<StudioDocument>("/api/v1/document-studio/documents", payload);
}

export function getStudioDocument(id: string) {
  return apiGet<StudioDocument>(`/api/v1/document-studio/documents/${id}`);
}

export function saveStudioDocument(id: string, payload: Partial<StudioDocument> & { expected_version?: number }) {
  return apiPatch<StudioDocument>(`/api/v1/document-studio/documents/${id}`, payload);
}

export function deleteStudioDocument(id: string) {
  return apiRequest<void>(`/api/v1/document-studio/documents/${id}`, { method: "DELETE" });
}

export function createStudioCheckpoint(id: string) {
  return apiPost<{ id: string; version: number; title: string; created_at: string }>(
    `/api/v1/document-studio/documents/${id}/revisions`,
    {},
  );
}

export function listStudioRevisions(id: string) {
  return apiGet<StudioRevision[]>(`/api/v1/document-studio/documents/${id}/revisions`);
}

export function listStudioCollaborators(id: string) {
  return apiGet<StudioCollaborator[]>(`/api/v1/document-studio/documents/${id}/collaborators`);
}

export function addStudioCollaborator(id: string, userId: string, permission: "view" | "edit") {
  return apiPost<StudioCollaborator>(`/api/v1/document-studio/documents/${id}/collaborators`, {
    user_id: userId,
    permission,
  });
}

export function removeStudioCollaborator(id: string, userId: string) {
  return apiRequest<void>(`/api/v1/document-studio/documents/${id}/collaborators/${userId}`, { method: "DELETE" });
}

export function downloadStudioDocument(id: string, format: "pdf" | "word") {
  return apiDownload(`/api/v1/document-studio/documents/${id}/export/${format}`);
}

export function saveBlobDownload(result: { blob: Blob; filename: string | null }, fallback: string) {
  const url = URL.createObjectURL(result.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = result.filename || fallback;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
