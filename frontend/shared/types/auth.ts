export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface QuotaInfo {
  search_cache_remaining_today: number;
  live_augment_remaining_month: number;
  manual_refresh_remaining_month: number;
}

export interface MeResponse {
  id: string;
  email: string;
  display_name: string | null;
  workspace_id: string;
  plan_tier: string;
  quotas: QuotaInfo;
}

export interface DevLoginRequest {
  email: string;
  display_name?: string;
}
