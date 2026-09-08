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

export type MedicalBenefit = {
  id: string;
  plan_id: string;
  code: string;
  name: string;
  category: string;
  description: string | null;
  annual_monetary_limit: string | null;
  per_event_limit: string | null;
  annual_visit_limit: number | null;
  requires_authorisation: boolean;
  is_active: boolean;
};

export type MedicalPlan = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  monthly_premium: string | null;
  currency: string;
  is_active: boolean;
  benefits: MedicalBenefit[];
};

export type MedicalDependant = {
  id: string;
  member_id: string;
  first_name: string;
  last_name: string;
  relationship_type: string;
  date_of_birth: string | null;
  status: string;
  created_at: string;
};

export type MedicalMember = {
  id: string;
  member_number: string;
  customer_id: string;
  plan_id: string;
  status: string;
  start_date: string;
  end_date: string | null;
  created_at: string;
  updated_at: string;
  dependants?: MedicalDependant[];
};

export type MedicalMemberList = {
  items: MedicalMember[];
  total: number;
  page: number;
  page_size: number;
};

export type MedicalClaim = {
  id: string;
  claim_number: string;
  member_id: string;
  dependant_id: string | null;
  claim_kind: string;
  status: string;
  service_date: string;
  admission_date: string | null;
  discharge_date: string | null;
  claim_amount: string;
  approved_amount: string | null;
  provider_name: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type BenefitBalance = {
  member_id: string;
  benefit_id: string;
  benefit_code: string;
  benefit_name: string;
  year: number;
  used_amount: string;
  remaining_amount: string | null;
  used_units: number;
  remaining_units: number | null;
};

export type GuaranteeEvent = {
  id: string;
  event_type: string;
  note: string | null;
  from_status: string | null;
  to_status: string | null;
  actor_user_id: string | null;
  created_at: string;
};

export type Guarantee = {
  id: string;
  guarantee_number: string;
  customer_id: string;
  guarantee_type: string;
  status: string;
  beneficiary: string;
  principal: string | null;
  tender_reference: string | null;
  contract_reference: string | null;
  currency: string;
  contract_value: string | null;
  guarantee_amount: string;
  issuer_name: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  assigned_user_id: string | null;
  created_at: string;
  updated_at: string;
  contract_description?: string | null;
  notes?: string | null;
  events?: GuaranteeEvent[];
};

export type GuaranteeList = {
  items: Guarantee[];
  total: number;
  page: number;
  page_size: number;
};

export type RiskRegisterItem = {
  id: string;
  assessment_id: string;
  category: string;
  title: string;
  description: string | null;
  likelihood: number;
  impact: number;
  inherent_score: number;
  inherent_level: string;
  existing_controls: string | null;
  treatment_plan: string | null;
  risk_owner: string | null;
  due_date: string | null;
  status: string;
  residual_likelihood: number | null;
  residual_impact: number | null;
  residual_score: number | null;
  residual_level: string | null;
  created_at: string;
  updated_at: string;
};

export type RiskAssessment = {
  id: string;
  assessment_number: string;
  customer_id: string;
  assessment_type: string;
  title: string;
  assessment_date: string;
  status: string;
  overall_level: string | null;
  assigned_user_id: string | null;
  created_at: string;
  updated_at: string;
  summary?: string | null;
  recommendations?: string | null;
  items?: RiskRegisterItem[];
};

export type RiskAssessmentList = {
  items: RiskAssessment[];
  total: number;
  page: number;
  page_size: number;
};

export type RiskDashboard = {
  assessments: number;
  open_items: number;
  high_or_critical_items: number;
  overdue_items: number;
};
