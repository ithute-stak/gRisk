export type AdminRole = {
  id: string;
  name: string;
  description: string | null;
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
};

export type AdminUserList = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
};

export type AuditEvent = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
};

export type AuditEventList = {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
};
