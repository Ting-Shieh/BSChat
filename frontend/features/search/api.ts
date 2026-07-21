import { apiFetch } from "@/shared/lib/api-client";
import type {
  SearchQueryResponse,
  SearchSessionDetail,
  SearchSessionListItem,
  SearchStatus,
} from "@/shared/types/search";

export async function fetchSearchStatus(token: string): Promise<SearchStatus> {
  return apiFetch<SearchStatus>("/api/v1/search/status", { token });
}

export async function createSearchQuery(
  token: string,
  body: { query_text: string; search_scope?: string; session_id?: string | null },
): Promise<SearchQueryResponse> {
  return apiFetch<SearchQueryResponse>("/api/v1/search/queries", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function fetchSearchQuery(token: string, queryId: string): Promise<SearchQueryResponse> {
  return apiFetch<SearchQueryResponse>(`/api/v1/search/queries/${queryId}`, { token });
}

export async function fetchSearchSessions(
  token: string,
): Promise<{ items: SearchSessionListItem[] }> {
  return apiFetch("/api/v1/search/sessions", { token });
}

export async function fetchSearchSession(
  token: string,
  sessionId: string,
): Promise<SearchSessionDetail> {
  return apiFetch(`/api/v1/search/sessions/${sessionId}`, { token });
}

export async function liveAugmentSearchQuery(
  token: string,
  queryId: string,
  body?: { contact_ids?: string[] },
): Promise<SearchQueryResponse> {
  return apiFetch<SearchQueryResponse>(`/api/v1/search/queries/${queryId}/live-augment`, {
    method: "POST",
    token,
    body: JSON.stringify(body ?? {}),
  });
}
