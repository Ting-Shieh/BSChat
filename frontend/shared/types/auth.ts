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

export interface SearchPrecisionInfo {
  mode: "strict" | "balanced" | "exploratory";
  can_use_exploratory: boolean;
}

export interface OrgMembershipInfo {
  org_id: string;
  org_name: string;
  role: string;
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
  search_precision: SearchPrecisionInfo;
  org_memberships?: OrgMembershipInfo[];
}

export interface DevLoginRequest {
  email: string;
  display_name?: string;
  plan_tier?: PlanTier;
  seed_org?: string;
}

export type PlanTier = "free" | "pro" | "enterprise";
