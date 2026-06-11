export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface QuotaInfo {
  search_cache_remaining_today: number;
  live_augment_remaining_month: number;
  manual_refresh_remaining_month: number;
  person_linkedin_remaining_month: number;
}

export interface PersonEnrichInfo {
  mode: string;
  auto_on_url: boolean;
}

export interface AutoRefreshInfo {
  enabled: boolean;
  interval_days: number;
}

export interface MeResponse {
  id: string;
  email: string;
  display_name: string | null;
  workspace_id: string;
  plan_tier: string;
  quotas: QuotaInfo;
  person_enrich: PersonEnrichInfo;
  auto_refresh: AutoRefreshInfo;
}

export interface DevLoginRequest {
  email: string;
  display_name?: string;
  plan_tier?: PlanTier;
}

export type PlanTier = "free" | "pro" | "enterprise";
