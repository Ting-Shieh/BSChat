export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthModeResponse {
  password_auth_enabled?: boolean;
  password_reset_email_enabled?: boolean;
  allow_dev_login: boolean;
  google_enabled: boolean;
  email_magic_link_enabled: boolean;
  email_domain_allowlist: string[];
  server_time: string;
}

export interface TeamInfo {
  org_id: string;
  org_name: string;
  slug: string;
}

export interface InvitePreview {
  org_id: string;
  org_name: string;
  slug: string;
  expires_at: string;
  seats_remaining: number;
}

export interface CreateInviteResponse {
  invite_id: string;
  token: string;
  org_id: string;
  org_name: string;
  expires_at: string;
  max_uses: number;
  join_path: string;
}

export interface QuotaInfo {
  search_cache_remaining_today: number;
  live_augment_remaining_month: number;
  manual_refresh_remaining_month: number;
  person_linkedin_remaining_month: number;
  public_recommend_remaining_lifetime?: number;
  public_recommend_unlimited?: boolean;
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
  is_enterprise?: boolean;
  is_primary_admin?: boolean;
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
