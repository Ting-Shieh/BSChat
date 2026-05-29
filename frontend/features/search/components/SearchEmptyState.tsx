"use client";

import Link from "next/link";
import type { SearchEmptyState } from "@/shared/types/search";

export function SearchEmptyState({ state }: { state: SearchEmptyState }) {
  const title =
    state.reason === "NO_INDEXED_CONTACTS"
      ? "還沒有可搜尋的聯絡人"
      : state.reason === "LOW_INDEX_COUNT"
        ? "聯絡人還不多"
        : "找不到符合的聯絡人";

  return (
    <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center">
      <p className="font-medium text-[var(--color-text-primary)]">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-[var(--color-text-secondary)]">
        {state.suggestions.map((suggestion) => (
          <li key={suggestion}>{suggestion}</li>
        ))}
      </ul>
      {state.cta?.action === "capture" && (
        <Link
          href="/capture"
          className="mt-4 inline-block rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white"
        >
          {state.cta.label}
        </Link>
      )}
    </div>
  );
}
