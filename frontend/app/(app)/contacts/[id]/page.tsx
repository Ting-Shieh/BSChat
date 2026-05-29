"use client";

import { useParams, useSearchParams } from "next/navigation";
import { ContactDetailPage } from "@/features/contacts/components/ContactDetailPage";
import { useContact } from "@/features/contacts/hooks";

export default function Page() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { data, isLoading } = useContact(params.id);

  if (isLoading || !data) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  return (
    <ContactDetailPage
      contact={data}
      fromSearch={searchParams.get("from_search")}
      searchRank={searchParams.get("rank")}
    />
  );
}
