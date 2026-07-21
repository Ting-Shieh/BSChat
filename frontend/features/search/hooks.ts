"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import type { SearchScope } from "@/shared/types/search";
import * as searchApi from "./api";

export function useSearchStatus() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["search", "status", token],
    queryFn: () => searchApi.fetchSearchStatus(token!),
    enabled: !!token,
  });
}

export function useSearch(scope: SearchScope = "private") {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { query_text: string; session_id?: string | null }) =>
      searchApi.createSearchQuery(token!, {
        query_text: body.query_text,
        search_scope: scope,
        session_id: body.session_id ?? undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["search", "sessions"] });
      qc.invalidateQueries({ queryKey: ["search", "status"] });
    },
  });
}

export function useSearchSessions(enabled = true) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["search", "sessions", token],
    queryFn: () => searchApi.fetchSearchSessions(token!),
    enabled: !!token && enabled,
  });
}

export function useSearchSessionDetail(sessionId: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["search", "session", sessionId, token],
    queryFn: () => searchApi.fetchSearchSession(token!, sessionId!),
    enabled: !!token && !!sessionId,
  });
}

export function useLiveAugment(queryId: string | undefined) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contactIds?: string[]) =>
      searchApi.liveAugmentSearchQuery(
        token!,
        queryId!,
        contactIds ? { contact_ids: contactIds } : undefined,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search", "status"] });
    },
  });
}

export function useSearchResultContext(
  queryId: string | null | undefined,
  contactId: string,
) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["search", "query", queryId, contactId, "context"],
    queryFn: async () => {
      const resp = await searchApi.fetchSearchQuery(token!, queryId!);
      const item = resp.results?.find((r) => r.contact_id === contactId);
      if (!item) return null;
      return {
        match_reason: item.match_reason,
        match_sources: item.match_sources ?? [],
      };
    },
    enabled: !!token && !!queryId && !!contactId,
  });
}

/** @deprecated use useSearchResultContext */
export function useSearchMatchReason(queryId: string | null | undefined, contactId: string) {
  const q = useSearchResultContext(queryId, contactId);
  return {
    ...q,
    data: q.data?.match_reason ?? null,
  };
}
