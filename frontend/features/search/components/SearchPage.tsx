"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import { useSearch, useSearchStatus } from "../hooks";
import { AhaMomentModal } from "./AhaMomentModal";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchInput } from "./SearchInput";
import { SearchResultCard } from "./SearchResultCard";

const AHA_KEY = "bschat-aha-shown";

export function SearchPage() {
  const { data: status, isLoading: statusLoading, isError: statusError } = useSearchStatus();
  const search = useSearch();
  const [showAha, setShowAha] = useState(false);
  const [draftQuery, setDraftQuery] = useState("");

  useEffect(() => {
    if (search.data?.aha_moment && !localStorage.getItem(AHA_KEY)) {
      setShowAha(true);
      localStorage.setItem(AHA_KEY, "1");
    }
  }, [search.data?.aha_moment]);

  const quotaZero = status ? status.quotas.search_cache_remaining_today <= 0 : false;
  const inputDisabled = search.isPending || (status != null && (quotaZero || !status.can_search));

  return (
    <main className="flex flex-col gap-4 p-4">
      <div>
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">AI 搜尋</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {statusLoading
            ? "載入中…"
            : status
              ? status.can_search && status.indexed_count < status.min_recommended
                ? `已收錄 ${status.indexed_count} 位 · 再多收幾張，搜尋會更準 · 今日剩餘 ${status.quotas.search_cache_remaining_today} 次`
                : `${status.indexed_count} 位可搜尋 · 今日剩餘 ${status.quotas.search_cache_remaining_today} 次`
              : "用對話從名片庫找商機"}
        </p>
      </div>

      <SearchInput
        disabled={inputDisabled}
        suggestions={status?.sample_queries ?? []}
        value={draftQuery}
        onValueChange={setDraftQuery}
        onSubmit={(q) => search.mutate(q)}
      />

      {statusError && (
        <p className="text-xs text-[var(--color-accent-hover)]">無法載入搜尋狀態，仍可直接搜尋。</p>
      )}

      {quotaZero && (
        <p className="text-xs text-[var(--color-accent-hover)]">今日搜尋額度已用完，明天再試。</p>
      )}

      {!statusLoading && status && !status.can_search && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-4 text-center text-sm text-[var(--color-text-secondary)]">
          先收錄幾張名片建立索引
          <Link href="/capture" className="mt-2 block text-[var(--color-primary)]">
            去收錄 →
          </Link>
        </div>
      )}

      {search.isPending && (
        <p className="animate-pulse text-sm text-[var(--color-text-secondary)]">正在比對你的名片庫…</p>
      )}

      {search.data?.status === "COMPLETED" && search.data.results && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-[var(--color-text-tertiary)]">
            找到 {search.data.result_count} 位
            {search.data.degraded ? "（簡化排序）" : ""}
            {search.data.latency_ms ? ` · ${search.data.latency_ms}ms` : ""}
          </p>
          {search.data.results.map((item) => (
            <SearchResultCard key={item.contact_id} item={item} queryId={search.data!.query_id} />
          ))}
        </div>
      )}

      {search.data?.status === "EMPTY" && search.data.empty_state && (
        <SearchEmptyState state={search.data.empty_state} />
      )}

      {search.isError && (
        <p className="text-sm text-[var(--color-error)]">搜尋失敗，請稍後再試。</p>
      )}

      <PrivacyStrip className="text-center" />
      {showAha && <AhaMomentModal onClose={() => setShowAha(false)} />}
    </main>
  );
}
