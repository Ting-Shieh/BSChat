import { API_BASE } from "./api-client";

const MEDIA_BASE = (
  process.env.NEXT_PUBLIC_MEDIA_BASE_URL?.replace(/\/$/, "") ||
  API_BASE.replace(/\/$/, "")
);

/**
 * Fallback when API returns a relative /uploads path (dev) or cached legacy payload.
 * Production: backend public_media_url() should return absolute URLs; this stays as safety net.
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${MEDIA_BASE}${url}`;
  return url;
}
