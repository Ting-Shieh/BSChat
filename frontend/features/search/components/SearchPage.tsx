"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMe } from "@/features/auth/hooks";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import type { SearchQueryResponse, SearchResultItem } from "@/shared/types/search";
import { cn } from "@/shared/lib/cn";
import { useLiveAugment, useSearch, useSearchStatus } from "../hooks";
import { AhaMomentModal } from "./AhaMomentModal";
import { DegradedSearchBanner } from "./DegradedSearchBanner";
import { SearchDebugPanel } from "./SearchDebugPanel";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchInput } from "./SearchInput";
import { SearchResultCard } from "./SearchResultCard";

const AHA_KEY = "bschat-aha-shown";
const SHOW_SEARCH_DEBUG = process.env.NODE_ENV === "development";

type ResultFilter = "all" | "private" | "network";

const RESULT_FILTERS: { id: ResultFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "private", label: "僅我的" },
  { id: "network", label: "僅公開" },
];

function isPublicResult(item: SearchResultItem) {
  return item.source_pool === "public_directory";
}

function filterResults(items: SearchResultItem[], filter: ResultFilter) {
  if (filter === "all") return items;
  if (filter === "network") return items.filter(isPublicResult);
  return items.filter((item) => !isPublicResult(item));
}

export function SearchPage() {
  const { data: me } = useMe();
  const isPro = me?.plan_tier === "pro" || me?.plan_tier === "enterprise";
  const apiScope = isPro ? "all" : "private";

  const { data: status, isLoading: statusLoading, isError: statusError } = useSearchStatus();
  const search = useSearch(apiScope);
  const [searchResult, setSearchResult] = useState<SearchQueryResponse | null>(null);
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const liveAugment = useLiveAugment(searchResult?.query_id);
  const [showAha, setShowAha] = useState(false);
  const [draftQuery, setDraftQuery] = useState("");

  useEffect(() => {
    if (search.data) {
      setSearchResult(search.data);
      setResultFilter("all");
    }
  }, [search.data]);

  useEffect(() => {
    if (searchResult?.aha_moment && !localStorage.getItem(AHA_KEY)) {
      setShowAha(true);
      localStorage.setItem(AHA_KEY, "1");
    }
  }, [searchResult?.aha_moment]);

  const quotaZero = status ? status.quotas.search_cache_remaining_today <= 0 : false;
  const liveQuotaZero = status ? status.quotas.live_augment_remaining_month <= 0 : false;
  const inputDisabled = search.isPending || (status != null && (quotaZero || !status.can_search));
  const liveBusy = liveAugment.isPending;

  const allResults = searchResult?.results ?? [];
  const visibleResults = useMemo(
    () => filterResults(allResults, resultFilter),
    [allResults, resultFilter],
  );

  const hasMixedResults = useMemo(() => {
    if (allResults.length === 0) return false;
    const hasPrivate = allResults.some((item) => !isPublicResult(item));
    const hasPublic = allResults.some(isPublicResult);
    return hasPrivate && hasPublic;
  }, [allResults]);

  const statusLine = () => {
    if (statusLoading) return "載入中…";
    if (!status) return "用對話從名片庫找商機";
    const parts = [`${status.indexed_count} 位可搜尋（你的名片庫）`];
    if (isPro && (status.public_pool_count ?? 0) > 0) {
      parts.push(`公開商務 ${status.public_pool_count} 位`);
    }
    parts.push(`今日剩餘 ${status.quotas.search_cache_remaining_today} 次`);
    return parts.join(" · ");
  };

  const handleSearch = (q: string) => {
    setResultFilter("all");
    search.mutate(q);
  };

  return (
    <main className="flex flex-col gap-4 p-4">
      <div>
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">AI 搜尋</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">{statusLine()}</p>
      </div>

      <SearchInput
        disabled={inputDisabled}
        suggestions={status?.sample_queries ?? []}
        value={draftQuery}
        onValueChange={setDraftQuery}
        onSubmit={handleSearch}
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
        <p className="animate-pulse text-sm text-[var(--color-text-secondary)]">
          {isPro ? "正在比對你的名片庫與公開商務…" : "正在比對…"}
        </p>
      )}

      {liveBusy && (
        <p className="animate-pulse text-sm text-[var(--color-text-secondary)]">正在即時查詢公司最新資訊…</p>
      )}

      {searchResult?.status === "COMPLETED" && searchResult.suggest_live && !liveQuotaZero && (
        <div className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
          <p className="text-sm text-[var(--color-ai-text)]">
            部分結果的公司資料可能已過期，可即時上網查最新產品資訊（本月剩{" "}
            {status?.quotas.live_augment_remaining_month ?? "—"} 次）。
          </p>
          <button
            type="button"
            disabled={liveBusy}
            onClick={() =>
              liveAugment.mutate(undefined, {
                onSuccess: (data) => setSearchResult(data),
              })
            }
            className="mt-3 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
          >
            即時查詢
          </button>
        </div>
      )}

      {searchResult?.status === "COMPLETED" && searchResult.suggest_live && liveQuotaZero && (
        <p className="text-xs text-[var(--color-text-secondary)]">
          本月即時查詢額度已用完（{status?.quotas.live_augment_remaining_month ?? 0} 次）。
        </p>
      )}

      {liveAugment.isError && (
        <p className="text-xs text-[var(--color-accent-hover)]">即時查詢失敗，請稍後再試。</p>
      )}

      {searchResult?.debug && SHOW_SEARCH_DEBUG && (
        <SearchDebugPanel debug={searchResult.debug} />
      )}

      {searchResult?.status === "COMPLETED" && searchResult.degraded && allResults.length > 0 && (
        <DegradedSearchBanner />
      )}

      {searchResult?.status === "COMPLETED" && allResults.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs text-[var(--color-text-tertiary)]">
              找到 {visibleResults.length} 位
              {resultFilter !== "all" ? `（共 ${allResults.length} 位）` : ""}
              {searchResult.degraded ? " · 簡化排序" : ""}
              {searchResult.latency_ms ? ` · ${searchResult.latency_ms}ms` : ""}
            </p>
            {isPro && (
              <div className="flex flex-wrap gap-1.5">
                {RESULT_FILTERS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setResultFilter(opt.id)}
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-[10px] font-medium transition-colors",
                      resultFilter === opt.id
                        ? "bg-[var(--color-primary)] text-white"
                        : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]",
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {hasMixedResults && resultFilter === "all" && (
            <p className="text-[10px] text-[var(--color-text-tertiary)]">
              藍標為你的名片庫 · 綠標為公開商務身份
            </p>
          )}

          {visibleResults.length === 0 ? (
            <p className="text-xs text-[var(--color-text-secondary)]">此篩選沒有符合的結果，試試其他篩選。</p>
          ) : (
            visibleResults.map((item) => (
              <SearchResultCard
                key={item.stub_id ?? item.contact_id ?? String(item.rank)}
                item={item}
                queryId={searchResult.query_id}
              />
            ))
          )}
        </div>
      )}

      {searchResult?.status === "EMPTY" && searchResult.empty_state && (
        <SearchEmptyState state={searchResult.empty_state} />
      )}

      {search.isError && (
        <p className="text-sm text-[var(--color-error)]">搜尋失敗，請稍後再試。</p>
      )}

      <PrivacyStrip className="text-center" />
      {showAha && <AhaMomentModal onClose={() => setShowAha(false)} />}
    </main>
  );
}
