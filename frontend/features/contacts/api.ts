import { apiFetch } from "@/shared/lib/api-client";
import type { ContactDetail, ContactListItem } from "@/shared/types/contact";

function auth(token: string) {
  return { token };
}

export async function listContacts(
  token: string,
  params: { page?: number; review_status?: string } = {},
): Promise<{ items: ContactListItem[]; total: number }> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.review_status) qs.set("review_status", params.review_status);
  const q = qs.toString();
  return apiFetch(`/api/v1/contacts${q ? `?${q}` : ""}`, auth(token));
}

export async function getContact(token: string, contactId: string): Promise<ContactDetail> {
  return apiFetch(`/api/v1/contacts/${contactId}`, auth(token));
}

export async function deleteContact(token: string, contactId: string): Promise<void> {
  return apiFetch(`/api/v1/contacts/${contactId}`, { method: "DELETE", ...auth(token) });
}

export type ContactUpdateFields = {
  display_name?: string;
  company_name?: string;
  title?: string;
  address?: string;
  website?: string;
  phone?: string;
  email?: string;
  linkedin_url?: string;
  person_scope?: string;
};

export async function updateContact(
  token: string,
  contactId: string,
  body: { version: number; fields: ContactUpdateFields },
): Promise<ContactDetail> {
  return apiFetch(`/api/v1/contacts/${contactId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    ...auth(token),
  });
}
