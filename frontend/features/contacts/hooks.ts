"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import * as contactsApi from "./api";

export function useContacts(params: { review_status?: string } = {}) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["contacts", params, token],
    queryFn: () => contactsApi.listContacts(token!, params),
    enabled: !!token,
    staleTime: 30_000,
  });
}

export function useContact(contactId: string) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["contacts", contactId, token],
    queryFn: () => contactsApi.getContact(token!, contactId),
    enabled: !!token && !!contactId,
    refetchInterval: (query) => {
      const data = query.state.data;
      const companyPending = data?.sections.company_enrichment.status === "pending";
      const personPending = data?.sections.ai_inferred.person_enrich?.status === "pending";
      return companyPending || personPending ? 3000 : false;
    },
  });
}
