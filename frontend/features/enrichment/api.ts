import { apiFetch } from "@/shared/lib/api-client";

export async function reEnrichCompany(
  token: string,
  companyId: string,
  contactId?: string,
): Promise<{ status: string; manual_refresh_remaining_month: number }> {
  const params = contactId ? `?contact_id=${encodeURIComponent(contactId)}` : "";
  return apiFetch(`/api/v1/companies/${companyId}/re-enrich${params}`, {
    method: "POST",
    token,
  });
}
