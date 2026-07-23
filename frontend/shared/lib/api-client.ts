const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** FastAPI `detail` code when body is `{"detail":"..."}`. */
  get detailCode(): string | null {
    try {
      const parsed = JSON.parse(this.message) as { detail?: unknown };
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      /* plain text */
    }
    return null;
  }
}

const API_ERROR_ZH: Record<string, string> = {
  INVITE_EXHAUSTED:
    "此邀請連結已使用過。若你已加入企業，請直接進入名片庫；尚未加入請請 Admin 撤銷後重發新邀請。",
  INVITE_REVOKED: "此邀請已被撤銷，請請 Admin 重新發送邀請。",
  INVITE_EXPIRED: "此邀請已過期，請請 Admin 重新發送邀請。",
  INVITE_NOT_FOUND: "找不到此邀請，連結可能無效或已刪除。",
  INVITE_NOT_USABLE: "此邀請已無法使用，請重新發送邀請。",
  EMAIL_MISMATCH: "請用受邀的 Email 登入後再加入。",
  INVITE_EMAIL_MISMATCH: "請用受邀的 Email 登入後再加入。",
  NOT_ORG_MEMBER: "對方須先是企業成員，才能加入子團隊。",
  NOT_OWNER: "只有子團隊負責人可以執行此操作。",
  ALREADY_MEMBER: "對方已在成員列表中。",
  PENDING_EXISTS: "已有待接受的邀請，請先撤銷再建新邀請。",
  NOT_ENTERPRISE_MEMBER: "你還不是企業成員。",
  NOT_ALLOWED: "沒有權限執行此操作。",
};

/** Human-readable message from ApiError / Error (maps known detail codes). */
export function formatApiError(err: unknown, fallback = "操作失敗，請稍後再試"): string {
  if (err instanceof ApiError) {
    const code = err.detailCode;
    if (code && API_ERROR_ZH[code]) return API_ERROR_ZH[code];
    if (code) return code;
    if (err.message && !err.message.trim().startsWith("{")) return err.message;
    return fallback;
  }
  if (err instanceof Error && err.message) {
    if (err.message.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(err.message) as { detail?: string };
        if (typeof parsed.detail === "string") {
          return API_ERROR_ZH[parsed.detail] ?? parsed.detail;
        }
      } catch {
        /* fall through */
      }
    }
    return err.message;
  }
  return fallback;
}

function handleUnauthorized() {
  if (typeof window === "undefined") return;
  // 動態 import 避免 SSR 循環依賴
  void import("@/features/auth/store").then(({ useAuthStore }) => {
    useAuthStore.getState().logout();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  });
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string; json?: boolean; skipUnauthorizedHandler?: boolean } = {},
): Promise<T> {
  const { token, headers, json = true, skipUnauthorizedHandler = false, ...rest } = options;
  const isFormData = rest.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      ...(json && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    if (res.status === 401 && !skipUnauthorizedHandler) {
      handleUnauthorized();
    }
    throw new ApiError(res.status, body || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export { API_BASE };
