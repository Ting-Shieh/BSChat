"use client";

import Link from "next/link";
import { EmptyState } from "@/shared/components/EmptyState";
import { useContacts } from "@/features/contacts/hooks";
import { ContactListCard } from "./ContactListCard";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

export function ContactsPage() {
  const { data, isLoading } = useContacts();
  const items = data?.items ?? [];

  if (isLoading) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  if (items.length === 0) {
    return (
      <main className="flex flex-col gap-6 p-4">
        <EmptyState
          title="尚無聯絡人"
          description="收錄名片並完成 OCR 後，聯絡人會自動出現在這裡。"
        />
        <Link
          href="/capture"
          className="rounded-xl bg-[var(--color-accent)] py-3 text-center font-medium text-white"
        >
          去收錄名片
        </Link>
        <PrivacyStrip />
      </main>
    );
  }

  return (
    <main className="flex flex-col gap-3 p-4">
      <p className="text-sm text-[var(--color-text-secondary)]">共 {data?.total ?? items.length} 位聯絡人</p>
      {items.map((c) => (
        <ContactListCard key={c.id} contact={c} />
      ))}
      <PrivacyStrip className="pt-2 text-center" />
    </main>
  );
}
