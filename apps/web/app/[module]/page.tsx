import AppShell from "@/components/AppShell";

const moduleCopy: Record<string, { title: string; description: string }> = {
  reports: { title: "Reports", description: "Management, regulatory and operational reporting will be delivered here." },
  finance: { title: "Finance", description: "Premium, billing, collections and finance controls will be delivered here." },
  risk: { title: "Risk", description: "Risk assessment and consulting workflows will be delivered here." },
  admin: { title: "Administration", description: "Platform, user and operational administration will be delivered here." },
  medical: { title: "Medical", description: "Medical aid and health cash plan workflows will be delivered here." },
};

export default async function ModulePage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  const item = moduleCopy[module] ?? { title: "Workspace", description: "This workspace is not available yet." };
  return (
    <AppShell>
      <div className="page-head"><div><h1>{item.title}</h1><p>{item.description}</p></div></div>
      <div className="card pad"><div className="notice">This module is intentionally staged for a later delivery phase. The active Next.js migration preserves the current customer, quotation, policy and claims workflows first.</div></div>
    </AppShell>
  );
}
