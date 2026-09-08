export type AuthUser = {
  id: string;
  email?: string;
  name?: string;
  roles: string[];
  isSuperuser: boolean;
};

export type CustomerSummary = {
  id: string;
  customer_number: string;
  customer_type: string;
  display_name: string;
  email: string | null;
  phone: string | null;
  status: string;
  created_at: string;
};

export type CustomerList = {
  items: CustomerSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type InsuranceProduct = {
  id: string;
  code: string;
  name: string;
  category: string;
  description: string | null;
  is_active: boolean;
};

export type QuoteItem = {
  id: string;
  label: string;
  description: string | null;
  amount: string;
};

export type Quote = {
  id: string;
  quote_number: string;
  customer_id: string;
  product_id: string;
  status: string;
  currency: string;
  sum_insured: string;
  premium: string;
  third_party_limit: string | null;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  created_at: string;
  items: QuoteItem[];
};

export type QuoteList = {
  items: Quote[];
  total: number;
  page: number;
  page_size: number;
};

export type Policy = {
  id: string;
  policy_number: string;
  customer_id: string;
  product_id: string;
  source_quote_id: string | null;
  status: string;
  currency: string;
  sum_insured: string;
  premium: string;
  start_date: string;
  end_date: string;
  created_at: string;
};

export type ClaimEvent = {
  id: string;
  event_type: string;
  note: string | null;
  from_status: string | null;
  to_status: string | null;
  actor_user_id: string | null;
  created_at: string;
};

export type Claim = {
  id: string;
  claim_number: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  incident_date: string;
  description: string;
  claim_amount: string;
  approved_amount: string | null;
  status: string;
  priority: string;
  assigned_user_id: string | null;
  reported_at: string;
  created_at: string;
  updated_at: string;
  events?: ClaimEvent[];
};

export type ClaimList = {
  items: Claim[];
  total: number;
  page: number;
  page_size: number;
};
