"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import * as captureApi from "./api";

export function useCards(params: { review_status?: string; session_id?: string; status?: string } = {}) {
  const token = useAuthStore((s) => s.token);
  const enabled = !!token && (params.session_id ? !!params.session_id : true);
  return useQuery({
    queryKey: ["cards", params, token],
    queryFn: () => captureApi.listCards(token!, params),
    enabled,
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const processing = items.some((c) =>
        ["uploading", "queued", "ocr_processing"].includes(c.status),
      );
      return processing ? 2000 : false;
    },
  });
}

export function useCard(cardId: string) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["card", cardId, token],
    queryFn: () => captureApi.getCard(token!, cardId),
    enabled: !!token && !!cardId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["uploading", "queued", "ocr_processing"].includes(status) ? 2000 : false;
    },
  });
}

export function usePendingCount() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["pending-count", token],
    queryFn: () => captureApi.getPendingCount(token!),
    enabled: !!token,
    refetchInterval: 5000,
  });
}

export function useCaptureSession(sessionId: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["capture-session", sessionId, token],
    queryFn: () => captureApi.getSession(token!, sessionId!),
    enabled: !!token && !!sessionId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      const cardsTotal = data.confirmed_count + data.pending_count;
      if (data.card_count > cardsTotal) return 2000;
      return false;
    },
  });
}
