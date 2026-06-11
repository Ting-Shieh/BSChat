import { apiFetch } from "@/shared/lib/api-client";

export type PersonEnrichResult = {
  status: string;
  person_scope?: string | null;
  confidence?: number | null;
  candidates?: Array<{
    index: number;
    linkedin_url?: string | null;
    headline?: string | null;
    match_score?: number;
  }>;
  quota_remaining?: number | null;
  error_code?: string | null;
};

function auth(token: string) {
  return { token };
}

export async function triggerPersonEnrich(
  token: string,
  contactId: string,
  confirmCandidateIndex?: number,
): Promise<PersonEnrichResult> {
  return apiFetch(`/api/v1/contacts/${contactId}/person-enrich`, {
    method: "POST",
    body: JSON.stringify(
      confirmCandidateIndex != null ? { confirm_candidate_index: confirmCandidateIndex } : {},
    ),
    ...auth(token),
  });
}

export async function confirmPersonEnrich(
  token: string,
  contactId: string,
  candidateIndex: number,
): Promise<PersonEnrichResult> {
  return apiFetch(`/api/v1/contacts/${contactId}/person-enrich/confirm`, {
    method: "POST",
    body: JSON.stringify({ candidate_index: candidateIndex }),
    ...auth(token),
  });
}

export async function rejectPersonEnrich(token: string, contactId: string): Promise<PersonEnrichResult> {
  return apiFetch(`/api/v1/contacts/${contactId}/person-enrich/reject`, {
    method: "POST",
    ...auth(token),
  });
}
