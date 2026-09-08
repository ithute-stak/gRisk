export type DocumentRecord = {
  id: string;
  customer_id: string | null;
  entity_type: string;
  entity_id: string | null;
  category: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  description: string | null;
  status: string;
  uploaded_by_user_id: string | null;
  created_at: string;
};

export type DocumentList = {
  items: DocumentRecord[];
  total: number;
  page: number;
  page_size: number;
};

export type Partner = {
  id: string;
  partner_number: string;
  partner_type: string;
  name: string;
  email: string | null;
  phone: string | null;
  website: string | null;
  external_reference: string | null;
  integration_status: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PartnerList = {
  items: Partner[];
  total: number;
  page: number;
  page_size: number;
};
