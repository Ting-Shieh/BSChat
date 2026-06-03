"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import { reEnrichCompany } from "./api";

export function useReEnrichCompany(contactId: string) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ companyId }: { companyId: string }) =>
      reEnrichCompany(token!, companyId, contactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts", contactId] });
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
