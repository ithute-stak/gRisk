export type Payment = {
  id: string;
  payment_number: string;
  invoice_id: string;
  customer_id: string;
  amount: string;
  currency: string;
  payment_date: string;
  payment_method: string;
  reference: string | null;
  notes: string | null;
  received_by_user_id: string | null;
  created_at: string;
};

export type Invoice = {
  id: string;
  invoice_number: string;
  customer_id: string;
  policy_id: string | null;
  medical_member_id: string | null;
  status: string;
  invoice_type: string;
  description: string;
  currency: string;
  amount_due: string;
  amount_paid: string;
  issue_date: string;
  due_date: string;
  created_at: string;
  updated_at: string;
  notes?: string | null;
  payments?: Payment[];
};

export type InvoiceList = {
  items: Invoice[];
  total: number;
  page: number;
  page_size: number;
};

export type FinanceDashboard = {
  invoices: number;
  outstanding_invoices: number;
  overdue_invoices: number;
  currency: string;
  total_invoiced: string;
  total_received: string;
  outstanding_balance: string;
};

export type NotificationItem = {
  id: string;
  user_id: string;
  customer_id: string | null;
  category: string;
  title: string;
  message: string;
  status: string;
  action_url: string | null;
  created_at: string;
  read_at: string | null;
};

export type NotificationList = {
  items: NotificationItem[];
  total: number;
  unread: number;
};

export type PortalUser = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
};

export type PortalAccess = {
  id: string;
  user_id: string;
  customer_id: string;
  portal_role: string;
  is_active: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PortalCustomer = {
  id: string;
  customer_number: string;
  display_name: string;
  customer_type: string;
  email: string | null;
  phone: string | null;
  portal_role: string;
};

export type PortalPolicy = {
  id: string;
  policy_number: string;
  product_id: string;
  status: string;
  currency: string;
  sum_insured: string;
  premium: string;
  start_date: string;
  end_date: string;
};

export type PortalClaim = {
  id: string;
  claim_number: string;
  policy_id: string;
  claim_type: string;
  incident_date: string;
  claim_amount: string;
  approved_amount: string | null;
  status: string;
};

export type PortalMedicalMember = {
  id: string;
  member_number: string;
  plan_id: string;
  status: string;
  start_date: string;
  end_date: string | null;
};

export type PortalGuarantee = {
  id: string;
  guarantee_number: string;
  guarantee_type: string;
  status: string;
  beneficiary: string;
  currency: string;
  guarantee_amount: string;
  expiry_date: string | null;
};

export type PortalInvoice = {
  id: string;
  invoice_number: string;
  status: string;
  invoice_type: string;
  description: string;
  currency: string;
  amount_due: string;
  amount_paid: string;
  issue_date: string;
  due_date: string;
};

export type PortalOverview = {
  customer: PortalCustomer;
  policies: PortalPolicy[];
  claims: PortalClaim[];
  medical_members: PortalMedicalMember[];
  guarantees: PortalGuarantee[];
  invoices: PortalInvoice[];
  outstanding_balance: string;
  unread_notifications: number;
};
