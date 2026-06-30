import { apiFetch } from "@/shared/lib/api-client";
import type {
  DevLoginRequest,
  MeResponse,
  PlanTier,
  TokenResponse,
} from "@/shared/types/auth";

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
