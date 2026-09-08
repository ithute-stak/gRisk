export type ExecutiveReport = {
  customers: number;
  active_policies: number;
  open_claims: number;
  active_medical_members: number;
  active_guarantees: number;
  open_risk_items: number;
  outstanding_invoices: number;
  total_policy_premium: string;
  total_claimed: string;
  total_claim_approved: string;
  total_received: string;
  outstanding_balance: string;
};

export type PortfolioReport = {
  quotes_by_status: Record<string, number>;
  policies_by_status: Record<string, number>;
  claims_by_status: Record<string, number>;
  medical_claims_by_status: Record<string, number>;
  guarantees_by_status: Record<string, number>;
  risk_items_by_level: Record<string, number>;
  invoices_by_status: Record<string, number>;
};

export type FinanceReport = {
  total_invoiced: string;
  total_received: string;
  outstanding_balance: string;
  overdue_balance: string;
  overdue_invoices: number;
  payments: number;
};

export type ClaimsReport = {
  general_claims: number;
  medical_claims: number;
  open_general_claims: number;
  open_medical_claims: number;
  general_claimed: string;
  general_approved: string;
  medical_claimed: string;
  medical_approved: string;
};
