import { apiFetch } from "@/shared/lib/api-client";
import type { DevLoginRequest, MeResponse, TokenResponse } from "@/shared/types/auth";

export async function devLogin(body: DevLoginRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/dev-login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMe(token: string): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/me", { token });
}
