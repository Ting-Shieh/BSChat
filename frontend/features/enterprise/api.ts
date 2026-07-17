import { apiFetch } from "@/shared/lib/api-client";

export interface EnterpriseApplication {
  id: string;
  company_name: string;
  slug_requested: string | null;
  contact_email: string;
  estimated_seats: number | null;
  note: string | null;
  status: string;
  resulting_org_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface EnterpriseInvitePreview {
  org_id: string;
  org_name: string;
  slug: string;
  invited_email: string | null;
  expires_at: string;
  is_enterprise: boolean;
}

export interface EnterpriseMember {
  user_id: string;
  email: string;
  display_name: string | null;
  role: string;
  is_primary_admin: boolean;
  joined_at: string;
}

export interface EnterpriseInviteItem {
  invite_id: string;
  invited_email: string | null;
  expires_at: string;
  use_count: number;
  max_uses: number;
  revoked_at: string | null;
  created_at: string;
}

export interface CreateEnterpriseInviteResponse {
  invite_id: string;
  token: string;
  org_id: string;
  org_name: string;
  invited_email: string;
  expires_at: string;
  join_path: string;
  email_sent: boolean;
}

export async function submitEnterpriseApplication(
  token: string,
  body: {
    company_name: string;
    contact_email: string;
    slug_requested?: string;
    estimated_seats?: number;
    note?: string;
  },
): Promise<EnterpriseApplication> {
  return apiFetch("/api/v1/enterprise/applications", {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export async function listMyEnterpriseApplications(
  token: string,
): Promise<EnterpriseApplication[]> {
  return apiFetch("/api/v1/enterprise/applications/mine", { token });
}

export async function previewEnterpriseInvite(
  inviteToken: string,
): Promise<EnterpriseInvitePreview> {
  return apiFetch(`/api/v1/enterprise/invites/${encodeURIComponent(inviteToken)}`);
}

export async function acceptEnterpriseInvite(
  token: string,
  inviteToken: string,
): Promise<{ org_id: string; org_name: string; slug: string }> {
  return apiFetch(`/api/v1/enterprise/invites/${encodeURIComponent(inviteToken)}/accept`, {
    method: "POST",
    token,
  });
}

export async function listEnterpriseMembers(
  token: string,
  orgId: string,
): Promise<EnterpriseMember[]> {
  return apiFetch(`/api/v1/enterprise/orgs/${orgId}/members`, { token });
}

export async function removeEnterpriseMember(
  token: string,
  orgId: string,
  userId: string,
): Promise<void> {
  await apiFetch(`/api/v1/enterprise/orgs/${orgId}/members/${userId}`, {
    method: "DELETE",
    token,
  });
}

export async function createEnterpriseInvite(
  token: string,
  orgId: string,
  body: { email: string; expires_days?: number },
): Promise<CreateEnterpriseInviteResponse> {
  return apiFetch(`/api/v1/enterprise/orgs/${orgId}/invites`, {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export async function listEnterpriseInvites(
  token: string,
  orgId: string,
): Promise<EnterpriseInviteItem[]> {
  return apiFetch(`/api/v1/enterprise/orgs/${orgId}/invites`, { token });
}

export async function revokeEnterpriseInvite(
  token: string,
  inviteId: string,
): Promise<void> {
  await apiFetch(`/api/v1/enterprise/invites/${inviteId}/revoke`, {
    method: "POST",
    token,
  });
}

export async function transferEnterpriseAdmin(
  token: string,
  orgId: string,
  newAdminUserId: string,
): Promise<unknown> {
  return apiFetch(`/api/v1/enterprise/orgs/${orgId}/transfer-admin`, {
    method: "POST",
    body: JSON.stringify({ new_admin_user_id: newAdminUserId }),
    token,
  });
}
