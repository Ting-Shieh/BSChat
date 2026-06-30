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
  public_pool_count?: number;
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

export interface StubPreview {
  display_name: string;
  company_name: string;
  title: string | null;
  product_keywords: string[];
}

export interface SearchResultItem {
  rank: number;
  match_score: number;
  match_reason: string;
  match_sources: MatchSource[];
  source_pool: string;
  contact_id?: string | null;
  contact_preview?: ContactPreview | null;
  stub_id?: string | null;
  stub_preview?: StubPreview | null;
  publisher_org_id?: string | null;
  publisher_org_name?: string | null;
  external_card_url?: string | null;
  live_products?: string[] | null;
}

export interface SearchEmptyState {
  reason: string;
  suggestions: string[];
  /** Pro (DDR-71): personalized suggestions from indexed contacts. */
  sample_queries: string[];
  cta?: { action: string; label: string } | null;
  search_precision?: string | null;
  precision_hint?: string | null;
}

export interface RetrievalCandidateDebug {
  id: string;
  label: string;
  retrieval_score: number;
}

export interface PoolRetrievalDebug {
  pool: string;
  lexical_query: string;
  semantic_query: string;
  ts_hits: number;
  trgm_extra_hits: number;
  vector_hits: number;
  widened: boolean;
  top_candidates: RetrievalCandidateDebug[];
}

export interface SearchDebugInfo {
  search_scope: string;
  search_precision: string;
  intent_prompt_version: string;
  rerank_prompt_version: string;
  semantic_query: string;
  parsed_intent: Record<string, unknown>;
  private?: PoolRetrievalDebug | null;
  public?: PoolRetrievalDebug | null;
  rerank_input_count: number;
  result_count: number;
  degraded: boolean;
  latency_ms?: number | null;
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
  debug?: SearchDebugInfo | null;
}

export type SearchScope = "private" | "network" | "all";
