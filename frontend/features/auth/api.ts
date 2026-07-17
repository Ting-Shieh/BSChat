import { apiFetch, API_BASE } from "@/shared/lib/api-client";
import type {
  AuthModeResponse,
  CreateInviteResponse,
  DevLoginRequest,
  InvitePreview,
  MeResponse,
  PlanTier,
  TeamInfo,
  TokenResponse,
} from "@/shared/types/auth";

export async function fetchAuthMode(): Promise<AuthModeResponse> {
  return apiFetch<AuthModeResponse>("/api/v1/auth/auth-mode");
}

export function googleStartUrl(inviteToken?: string): string {
  const q = new URLSearchParams();
  if (inviteToken) q.set("invite_token", inviteToken);
  q.set("next", "/contacts");
  return `${API_BASE}/api/v1/auth/google/start?${q.toString()}`;
}

export async function registerAccount(body: {
  email: string;
  password: string;
  display_name?: string;
  invite_token?: string;
}): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
    skipUnauthorizedHandler: true,
  });
}

export async function passwordLogin(body: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
    skipUnauthorizedHandler: true,
  });
}

export async function forgotPassword(email: string): Promise<{ sent: boolean }> {
  return apiFetch("/api/v1/auth/password/forgot", {
    method: "POST",
    body: JSON.stringify({ email }),
    skipUnauthorizedHandler: true,
  });
}

export async function resetPassword(body: {
  token: string;
  new_password: string;
}): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/password/reset", {
    method: "POST",
    body: JSON.stringify(body),
    skipUnauthorizedHandler: true,
  });
}

export async function requestMagicLink(
  email: string,
  invite_token?: string,
): Promise<{ sent: boolean; debug_link?: string | null }> {
  return apiFetch("/api/v1/auth/magic-link", {
    method: "POST",
    body: JSON.stringify({ email, invite_token: invite_token || null }),
  });
}

export async function devLogin(body: DevLoginRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/dev-login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMe(token: string): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/me", { token });
}

export async function switchPlan(token: string, plan_tier: PlanTier): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/me/plan", {
    method: "POST",
    body: JSON.stringify({ plan_tier }),
    token,
  });
}

export async function updateSettings(
  token: string,
  body: {
    auto_refresh_enabled?: boolean;
    auto_refresh_interval_days?: number;
    person_linkedin_auto_on_url?: boolean;
    search_precision?: string;
  },
): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/me/settings", {
    method: "PATCH",
    body: JSON.stringify(body),
    token,
  });
}

export async function createTeam(
  token: string,
  body: { name: string; slug: string },
): Promise<TeamInfo> {
  return apiFetch<TeamInfo>("/api/v1/teams", {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export async function createInvite(
  token: string,
  body: { org_id: string; expires_days?: number; max_uses?: number },
): Promise<CreateInviteResponse> {
  return apiFetch<CreateInviteResponse>("/api/v1/invites", {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export async function previewInvite(inviteToken: string): Promise<InvitePreview> {
  return apiFetch<InvitePreview>(`/api/v1/invites/${encodeURIComponent(inviteToken)}`);
}

export async function acceptInvite(token: string, inviteToken: string): Promise<TeamInfo> {
  return apiFetch<TeamInfo>(`/api/v1/invites/${encodeURIComponent(inviteToken)}/accept`, {
    method: "POST",
    token,
  });
}
