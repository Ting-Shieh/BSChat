import { apiFetch } from "@/shared/lib/api-client";

export interface OrgSummary {
  id: string;
  name: string;
  slug: string;
  published_stub_count: number;
}

export interface PublicStub {
  id: string;
  org_id: string;
  display_name: string;
  company_name: string;
  title: string | null;
  responsibility_keywords: string[];
  product_keywords: string[];
  external_card_url: string;
  status: "draft" | "published" | "unpublished";
  published_at: string | null;
  unpublished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StubPayload {
  display_name: string;
  company_name: string;
  title?: string | null;
  responsibility_keywords?: string[];
  product_keywords?: string[];
  external_card_url: string;
}

export async function fetchMyOrgs(token: string): Promise<{ items: OrgSummary[] }> {
  return apiFetch("/api/v1/orgs/mine", { token });
}

export async function fetchStubs(
  token: string,
  orgId: string,
  status?: string,
): Promise<{ items: PublicStub[] }> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch(`/api/v1/orgs/${orgId}/stubs${qs}`, { token });
}

export async function createStub(token: string, orgId: string, body: StubPayload): Promise<PublicStub> {
  return apiFetch(`/api/v1/orgs/${orgId}/stubs`, {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export type StubUpdatePayload = Partial<StubPayload>;

export async function updateStub(
  token: string,
  orgId: string,
  stubId: string,
  body: StubUpdatePayload,
): Promise<PublicStub> {
  return apiFetch(`/api/v1/orgs/${orgId}/stubs/${stubId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    token,
  });
}

export async function publishStub(token: string, orgId: string, stubId: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/orgs/${orgId}/stubs/${stubId}/publish`, {
    method: "POST",
    token,
  });
}

export async function unpublishStub(token: string, orgId: string, stubId: string): Promise<PublicStub> {
  return apiFetch(`/api/v1/orgs/${orgId}/stubs/${stubId}/unpublish`, {
    method: "POST",
    token,
  });
}

export async function deleteStub(token: string, orgId: string, stubId: string): Promise<void> {
  await apiFetch(`/api/v1/orgs/${orgId}/stubs/${stubId}`, {
    method: "DELETE",
    token,
  });
}

export async function importStubsCsv(
  token: string,
  orgId: string,
  file: File,
  autoPublish = false,
): Promise<{ imported: number; skipped: number; errors: { row: number; reason: string }[] }> {
  const form = new FormData();
  form.append("file", file);
  const qs = autoPublish ? "?auto_publish=true" : "";
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const res = await fetch(`${base}/api/v1/orgs/${orgId}/stubs/import-csv${qs}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}
