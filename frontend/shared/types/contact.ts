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
  source_type: string | null;
  source_label: string | null;
  review_status: string;
  image_url: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  sections: {
    card_original: { fields: ProvenanceField[]; image_url: string | null };
    ai_inferred: { responsibility_scope: Record<string, unknown> | null };
    company_enrichment: CompanyEnrichmentSection;
  };
}
