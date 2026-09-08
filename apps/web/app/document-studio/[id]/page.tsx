"use client";

import { useParams } from "next/navigation";
import DocumentStudioEditor from "@/components/DocumentStudioEditor";

export default function DocumentStudioEditorPage() {
  const params = useParams<{ id: string }>();
  return <DocumentStudioEditor documentId={params.id} />;
}
