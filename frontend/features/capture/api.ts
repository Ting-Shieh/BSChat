import { apiFetch, ApiError } from "@/shared/lib/api-client";
import type {
  CaptureSession,
  CardDetail,
  CardListItem,
  ImportCardResponse,
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

export async function skipReviewCard(token: string, cardId: string): Promise<CardDetail> {
  return apiFetch(`/api/v1/cards/${cardId}/skip`, {
    method: "POST",
    ...auth(token),
  });
}

export async function deleteCard(token: string, cardId: string): Promise<void> {
  await apiFetch(`/api/v1/cards/${cardId}`, {
    method: "DELETE",
    ...auth(token),
  });
}

export async function reocrCard(token: string, cardId: string): Promise<{ raw_card_id: string; status: string }> {
  return apiFetch(`/api/v1/cards/${cardId}/reocr`, {
    method: "POST",
    ...auth(token),
  });
}

function importErrorMessage(err: unknown): never {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message) as {
        detail?: { code?: string; message?: string } | string;
      };
      const detail = parsed.detail;
      if (detail && typeof detail === "object" && detail.message) {
        throw new Error(detail.message);
      }
      if (typeof detail === "string") {
        throw new Error(detail);
      }
    } catch (parseErr) {
      if (parseErr instanceof Error && parseErr.message !== err.message) {
        throw parseErr;
      }
    }
    throw new Error(err.message || "匯入失敗");
  }
  throw err instanceof Error ? err : new Error("匯入失敗");
}

export async function importUrl(
  token: string,
  url: string,
  options: { force?: boolean } = {},
): Promise<ImportCardResponse> {
  try {
    return await apiFetch("/api/v1/cards/import-url", {
      method: "POST",
      body: JSON.stringify({ url, force: options.force ?? false }),
      ...auth(token),
    });
  } catch (err) {
    importErrorMessage(err);
  }
}

export async function importQr(token: string, payload: string): Promise<ImportCardResponse> {
  try {
    return await apiFetch("/api/v1/cards/import-qr", {
      method: "POST",
      body: JSON.stringify({ payload }),
      ...auth(token),
    });
  } catch (err) {
    importErrorMessage(err);
  }
}
