const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
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
  options: RequestInit & { token?: string; json?: boolean } = {},
): Promise<T> {
  const { token, headers, json = true, ...rest } = options;
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
    if (res.status === 401) {
      handleUnauthorized();
    }
    throw new ApiError(res.status, body || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export { API_BASE };
