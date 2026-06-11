"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import * as contactsApi from "@/features/contacts/api";
import type { ContactDetail } from "@/shared/types/contact";
import * as api from "./api";
import type { PersonEnrichResult } from "./api";

function contactQueryKey(contactId: string, token: string | null) {
  return ["contacts", contactId, token] as const;
}

function mapEnrichStatus(result: PersonEnrichResult): string {
  if (result.status === "completed") return "completed";
  if (result.status === "insufficient") return "insufficient";
  if (result.status === "needs_confirmation") return "needs_confirmation";
  return result.status;
}

function applyPersonEnrichResult(contact: ContactDetail, result: PersonEnrichResult): ContactDetail {
  const pe = contact.sections.ai_inferred.person_enrich;
  if (!pe) return contact;

  const status = mapEnrichStatus(result);
  const quotaRemaining = result.quota_remaining ?? pe.quota_remaining;
  const canEnrich =
    quotaRemaining != null && quotaRemaining >= 0 ? quotaRemaining > 0 : pe.can_enrich;

  return {
    ...contact,
    sections: {
      ...contact.sections,
      ai_inferred: {
        ...contact.sections.ai_inferred,
        person_enrich: {
          ...pe,
          status,
          person_scope: result.person_scope ?? pe.person_scope,
          confidence: result.confidence ?? pe.confidence,
          quota_remaining: quotaRemaining,
          can_enrich: canEnrich,
          candidates: result.candidates ?? pe.candidates,
        },
      },
    },
  };
}

function applyPersonEnrichPending(contact: ContactDetail): ContactDetail {
  const pe = contact.sections.ai_inferred.person_enrich;
  if (!pe) return contact;

  return {
    ...contact,
    sections: {
      ...contact.sections,
      ai_inferred: {
        ...contact.sections.ai_inferred,
        person_enrich: {
          ...pe,
          status: "pending",
          can_enrich: false,
        },
      },
    },
  };
}

export function usePersonEnrichMutations(contactId: string) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const key = contactQueryKey(contactId, token);

  const invalidate = async () => {
    await queryClient.refetchQueries({ queryKey: ["contacts", contactId] });
    queryClient.invalidateQueries({ queryKey: ["contacts"] });
    queryClient.invalidateQueries({ queryKey: ["me"] });
  };

  const enrich = useMutation({
    mutationFn: () => api.triggerPersonEnrich(token!, contactId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<ContactDetail>(key);
      if (previous) {
        queryClient.setQueryData(key, applyPersonEnrichPending(previous));
      }
      return { previous };
    },
    onSuccess: async (result) => {
      const prev = queryClient.getQueryData<ContactDetail>(key);
      if (prev) {
        queryClient.setQueryData(key, applyPersonEnrichResult(prev, result));
      }
      await invalidate();
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
    },
  });

  const confirm = useMutation({
    mutationFn: (candidateIndex: number) => api.confirmPersonEnrich(token!, contactId, candidateIndex),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<ContactDetail>(key);
      if (previous) {
        queryClient.setQueryData(key, applyPersonEnrichPending(previous));
      }
      return { previous };
    },
    onSuccess: async (result) => {
      const prev = queryClient.getQueryData<ContactDetail>(key);
      if (prev) {
        queryClient.setQueryData(key, applyPersonEnrichResult(prev, result));
      }
      await invalidate();
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
    },
  });

  const reject = useMutation({
    mutationFn: () => api.rejectPersonEnrich(token!, contactId),
    onSuccess: invalidate,
  });

  const saveScope = useMutation({
    mutationFn: ({ version, person_scope }: { version: number; person_scope: string }) =>
      contactsApi.updateContact(token!, contactId, { version, fields: { person_scope } }),
    onSuccess: (updated) => {
      queryClient.setQueryData(key, updated);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });

  return { enrich, confirm, reject, saveScope };
}
