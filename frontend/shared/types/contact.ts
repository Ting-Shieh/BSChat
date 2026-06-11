export interface ContactListItem {
  id: string;
  display_name: string | null;
  company_name: string | null;
  title: string | null;
  responsibility_scope: string | null;
  responsibility_confidence: number | null;
  source_label: string | null;
  review_status: string;
  image_url: string | null;
  phones_preview: string | null;
  emails_preview: string | null;
  company_products_preview?: string | null;
  company_enrichment_status?: string | null;
}

export interface CompanyEnrichmentSection {
  status: string;
  main_products?: string[] | null;
  website_url?: string | null;
  confidence?: number | null;
  provenance_label?: string | null;
  updated_at?: string | null;
  can_refresh?: boolean;
  refresh_quota_remaining?: number | null;
  review_status?: string | null;
  needs_review?: boolean | null;
}

export interface PersonEnrichCandidate {
  index: number;
  linkedin_url?: string | null;
  headline?: string | null;
  match_score?: number;
}

export type PersonScopeDataSource =
  | "linkedin_profile"
  | "linkedin_search"
  | "card_inference"
  | "linkedin_url_public"
  | "user_manual"
  | string;

export interface PersonEnrichSection {
  status: string;
  is_pro: boolean;
  person_scope?: string | null;
  confidence?: number | null;
  data_source?: PersonScopeDataSource | null;
  message?: string | null;
  has_m3_fallback?: boolean;
  provenance_label?: string | null;
  updated_at?: string | null;
  candidates?: PersonEnrichCandidate[] | null;
  quota_remaining?: number | null;
  can_enrich?: boolean;
  has_linkedin_url?: boolean;
}

export interface ProvenanceField {
  name: string;
  value: string | null;
  source: string;
  confidence: number | null;
}

export interface ContactDetail {
  id: string;
  company_id?: string | null;
  display_name: string | null;
  company_name: string | null;
  title: string | null;
  phones: Array<{ value: string; primary?: boolean }>;
  emails: Array<{ value: string; primary?: boolean }>;
  address: string | null;
  website: string | null;
  linkedin_url?: string | null;
  source_type: string | null;
  source_label: string | null;
  review_status: string;
  image_url: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  sections: {
    card_original: { fields: ProvenanceField[]; image_url: string | null };
    ai_inferred: {
      responsibility_scope: Record<string, unknown> | null;
      person_enrich?: PersonEnrichSection | null;
    };
    company_enrichment: CompanyEnrichmentSection;
  };
}
