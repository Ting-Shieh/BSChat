import { apiFetch } from "@/shared/lib/api-client";
import type {
  CaptureSession,
  CardDetail,
  CardListItem,
  RawCardUploadResponse,
} from "@/shared/types/capture";

function auth(token: string) {
  return { token };
}

export async function createSession(
  token: string,
  body: { source_type?: string; source_label?: string } = {},
): Promise<CaptureSession> {
  return apiFetch("/api/v1/capture-sessions", {
    method: "POST",
    body: JSON.stringify(body),
    ...auth(token),
  });
}

export async function getSession(token: string, sessionId: string): Promise<CaptureSession> {
  return apiFetch(`/api/v1/capture-sessions/${sessionId}`, auth(token));
}

export async function closeSession(
  token: string,
  sessionId: string,
  sourceLabel?: string,
): Promise<CaptureSession> {
  return apiFetch(`/api/v1/capture-sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "closed", source_label: sourceLabel }),
    ...auth(token),
  });
}

export async function uploadCard(
  token: string,
  sessionId: string,
  file: File,
  idempotencyKey: string,
): Promise<RawCardUploadResponse> {
  const form = new FormData();
  form.append("image", file);
  return apiFetch(`/api/v1/capture-sessions/${sessionId}/cards`, {
    method: "POST",
    body: form,
    headers: { "Idempotency-Key": idempotencyKey },
    json: false,
    ...auth(token),
  });
}

export async function listCards(
  token: string,
  params: { review_status?: string; session_id?: string; status?: string } = {},
): Promise<{ items: CardListItem[] }> {
  const qs = new URLSearchParams();
  if (params.review_status) qs.set("review_status", params.review_status);
  if (params.session_id) qs.set("session_id", params.session_id);
  if (params.status) qs.set("status", params.status);
  const q = qs.toString();
  return apiFetch(`/api/v1/cards${q ? `?${q}` : ""}`, auth(token));
}

export async function getCard(token: string, cardId: string): Promise<CardDetail> {
  return apiFetch(`/api/v1/cards/${cardId}`, auth(token));
}

export async function getPendingCount(token: string): Promise<{ count: number }> {
  return apiFetch("/api/v1/cards/pending-count", auth(token));
}

export async function reviewCard(
  token: string,
  cardId: string,
  body: { name?: string; company?: string; title?: string; version: number },
): Promise<CardDetail> {
  return apiFetch(`/api/v1/cards/${cardId}/review`, {
    method: "PATCH",
    body: JSON.stringify(body),
    ...auth(token),
  });
}

export async function reocrCard(token: string, cardId: string): Promise<{ raw_card_id: string; status: string }> {
  return apiFetch(`/api/v1/cards/${cardId}/reocr`, {
    method: "POST",
    ...auth(token),
  });
}
