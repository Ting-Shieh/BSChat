import { apiFetch } from "@/shared/lib/api-client";
import type { SearchQueryResponse, SearchStatus } from "@/shared/types/search";

export async function fetchSearchStatus(token: string): Promise<SearchStatus> {
  return apiFetch<SearchStatus>("/api/v1/search/status", { token });
}

export async function createSearchQuery(
  token: string,
  body: { query_text: string; search_scope?: string },
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
