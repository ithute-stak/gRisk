"use client";

import "../studio.css";
import "../loanhub-editor.css";
import "../official-letterhead.css";
import "../stamp-preview-cleanup.css";
import { useParams } from "next/navigation";
import LoanHubDocumentStudioEditor from "@/components/LoanHubDocumentStudioEditor";
import StudioLetterheadCustomization from "@/components/StudioLetterheadCustomization";

export default function DocumentStudioEditorPage() {
  const params = useParams<{ id: string }>();
  return <>
    <LoanHubDocumentStudioEditor documentId={params.id} />
    <StudioLetterheadCustomization documentId={params.id} />
  </>;
}
