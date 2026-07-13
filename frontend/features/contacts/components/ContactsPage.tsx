"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { EmptyState } from "@/shared/components/EmptyState";
import { useContacts } from "@/features/contacts/hooks";
import { ContactListCard } from "./ContactListCard";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import { cn } from "@/shared/lib/cn";

type ListFilter = "all" | "dormant" | "unconfirmed";

const DORMANT_THRESHOLD = 6;

const FILTERS: { id: ListFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "dormant", label: "💤 沉睡" },
  { id: "unconfirmed", label: "待確認" },
];

export function ContactsPage() {
  const { data, isLoading } = useContacts();
  const [filter, setFilter] = useState<ListFilter>("all");
  const items = data?.items ?? [];

  const counts = useMemo(() => {
    const dormant = items.filter((c) => (c.dormant_months ?? 0) >= DORMANT_THRESHOLD).length;
    const unconfirmed = items.filter((c) => c.review_status === "unconfirmed").length;
    return { all: items.length, dormant, unconfirmed };
  }, [items]);

  const visible = useMemo(() => {
    if (filter === "dormant") {
      return items.filter((c) => (c.dormant_months ?? 0) >= DORMANT_THRESHOLD);
    }
    if (filter === "unconfirmed") {
      return items.filter((c) => c.review_status === "unconfirmed");
    }
    return items;
  }, [items, filter]);

  if (isLoading) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  if (items.length === 0) {
    return (
      <main className="flex flex-col gap-6 p-4">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">名片庫</h1>
          <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">尚無聯絡人</p>
        </div>
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
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">名片庫</h1>
        <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">
          {data?.total ?? items.length} 位聯絡人
        </p>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {FILTERS.map((f) => {
          const count =
            f.id === "all" ? counts.all : f.id === "dormant" ? counts.dormant : counts.unconfirmed;
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={cn(
                "shrink-0 rounded-full px-3 py-1.5 text-[11px] font-medium transition-colors",
                active
                  ? "bg-[var(--color-primary)] text-white"
                  : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]",
              )}
            >
              {f.label} {count}
            </button>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">此分類尚無聯絡人</p>
      ) : (
        visible.map((c) => <ContactListCard key={c.id} contact={c} />)
      )}
      <PrivacyStrip className="pt-2 text-center" />
    </main>
  );
}
