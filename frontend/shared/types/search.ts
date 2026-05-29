export interface SearchQuotas {
  search_cache_remaining_today: number;
  live_augment_remaining_month: number;
}

export interface SearchStatus {
  indexed_count: number;
  can_search: boolean;
  min_recommended: number;
  /** Pro (DDR-71): personalized suggestions from indexed contacts. */
  sample_queries: string[];
  quotas: SearchQuotas;
}

export interface MatchSource {
  field: string;
  value: string;
  confidence?: number | null;
}

export interface ContactPreview {
  display_name: string | null;
  company_name: string | null;
  title: string | null;
  review_status: string;
  phones: string[];
  emails: string[];
  image_url: string | null;
}

export interface SearchResultItem {
  contact_id: string;
  rank: number;
  match_score: number;
  match_reason: string;
  match_sources: MatchSource[];
  source_pool: string;
  contact_preview: ContactPreview;
}

export interface SearchEmptyState {
  reason: string;
  suggestions: string[];
  /** Pro (DDR-71): personalized suggestions from indexed contacts. */
  sample_queries: string[];
  cta?: { action: string; label: string } | null;
}

export interface SearchQueryResponse {
  query_id: string;
  status: string;
  result_count?: number;
  latency_ms?: number | null;
  degraded?: boolean;
  aha_moment?: boolean;
  suggest_live?: boolean;
  results?: SearchResultItem[];
  empty_state?: SearchEmptyState;
}
