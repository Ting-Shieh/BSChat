"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMe } from "@/features/auth/hooks";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import type { SearchQueryResponse, SearchResultItem } from "@/shared/types/search";
import { useLiveAugment, useSearch, useSearchStatus } from "../hooks";
import { AhaMomentModal } from "./AhaMomentModal";
import { DegradedSearchBanner } from "./DegradedSearchBanner";
import { SearchDebugPanel } from "./SearchDebugPanel";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchInput } from "./SearchInput";
import { SearchPlanPanel } from "./SearchPlanPanel";
import { SearchResultCard } from "./SearchResultCard";

const AHA_KEY = "bschat-aha-shown";
const SHOW_SEARCH_DEBUG = process.env.NODE_ENV === "development";

function isPublicResult(item: SearchResultItem) {
  return item.source_pool === "public_directory";
}

export function SearchPage() {
  const { data: me } = useMe();
  const { data: status, isLoading: statusLoading, isError: statusError } = useSearchStatus();

  const unlimited =
    status?.public_recommend_unlimited ?? me?.quotas.public_recommend_unlimited ?? false;
  const remaining =
    status?.public_recommend_remaining_lifetime ??
    me?.quotas.public_recommend_remaining_lifetime ??
    0;
  const canUsePublic = status?.can_use_public_recommend ?? (unlimited || remaining > 0);
  const poolCount = status?.public_pool_count ?? 0;
  const includePublicPool = canUsePublic && poolCount > 0;
  const publicSkipReason = !canUsePublic ? "trial" : poolCount === 0 ? "empty" : "trial";
  const apiScope = canUsePublic ? "all" : "private";

  const search = useSearch(apiScope);
  const [searchResult, setSearchResult] = useState<SearchQueryResponse | null>(null);
  const liveAugment = useLiveAugment(searchResult?.query_id);
  const [showAha, setShowAha] = useState(false);
  const [draftQuery, setDraftQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [planSession, setPlanSession] = useState(0);

  useEffect(() => {
    if (search.data) {
      setSearchResult(search.data);
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
  const privateResults = useMemo(
    () => allResults.filter((item) => !isPublicResult(item)),
    [allResults],
  );
  const publicResults = useMemo(() => allResults.filter(isPublicResult), [allResults]);

  const showPlan = search.isPending || (submittedQuery != null && searchResult != null);
  const planFinished =
    !search.isPending &&
    searchResult != null &&
    (searchResult.status === "COMPLETED" || searchResult.status === "EMPTY");

  const statusLine = () => {
    if (statusLoading) return "載入中…";
    if (!status) return "用對話從名片庫找商機";
    const parts = [`${status.indexed_count} 位可搜尋（你的名片庫）`];
    if (canUsePublic && (status.public_pool_count ?? 0) > 0) {
      parts.push(`公開商務 ${status.public_pool_count} 位`);
    }
    if (unlimited) {
      parts.push("公開推薦無限");
    } else if (canUsePublic) {
      parts.push(`公開試用剩 ${remaining}`);
    }
    parts.push(`今日剩餘 ${status.quotas.search_cache_remaining_today} 次`);
    return parts.join(" · ");
  };

  const handleSearch = (q: string) => {
    setSubmittedQuery(q);
    setSearchResult(null);
    setPlanSession((n) => n + 1);
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

      {submittedQuery && (
        <div className="flex justify-end">
          <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--color-primary)] px-3.5 py-2.5 text-[14px] leading-relaxed text-white">
            {submittedQuery}
          </div>
        </div>
      )}

      {showPlan && (
        <SearchPlanPanel
          key={planSession}
          running={search.isPending}
          finished={planFinished}
          includePublicPool={includePublicPool}
          publicSkipReason={publicSkipReason}
          indexedHint={status?.indexed_count}
        />
      )}

      {search.isPending && (
        <p className="animate-pulse text-center text-xs text-[var(--color-text-tertiary)]">
          正在向伺服器搜尋（含 AI 排序），請勿關閉頁面…
        </p>
      )}

      {search.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
          搜尋失敗（後端逾時或連線中斷）。請再送一次，或確認 API 仍在跑。
          <button
            type="button"
            className="ml-2 font-medium underline"
            onClick={() => submittedQuery && handleSearch(submittedQuery)}
          >
            重試
          </button>
        </div>
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
          {searchResult.briefing && (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--color-primary)] text-sm text-white">
                  ✦
                </span>
                <span className="text-[13px] font-semibold text-[var(--color-primary)]">商機簡報</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-primary)]">
                {searchResult.briefing.headline}
              </p>
              {searchResult.latency_ms ? (
                <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
                  {searchResult.latency_ms}ms
                  {searchResult.degraded ? " · 簡化排序" : ""}
                </p>
              ) : null}
            </div>
          )}

          {privateResults.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-[11px] font-bold tracking-wide text-[var(--color-text-tertiary)]">
                你的名片庫 · 團隊池
              </p>
              {privateResults.map((item) => (
                <SearchResultCard
                  key={item.stub_id ?? item.contact_id ?? `p-${item.rank}`}
                  item={item}
                  queryId={searchResult.query_id}
                />
              ))}
            </div>
          )}

          {(publicResults.length > 0 || (canUsePublic && privateResults.length > 0)) && (
            <div className="flex flex-col gap-2">
              <p className="text-[11px] font-bold tracking-wide text-[var(--color-text-tertiary)]">
                AI 推薦 · 公開身份
              </p>
              {publicResults.length === 0 ? (
                <p className="rounded-xl border border-dashed border-[var(--color-border)] px-3 py-3 text-xs text-[var(--color-text-secondary)]">
                  {poolCount === 0
                    ? "目前沒有可推薦的公開身份（或尚未有企業公開名片）。"
                    : "本次未從公開池配對到合適人選。"}
                </p>
              ) : (
                publicResults.map((item) => (
                  <SearchResultCard
                    key={item.stub_id ?? item.contact_id ?? `pub-${item.rank}`}
                    item={item}
                    queryId={searchResult.query_id}
                  />
                ))
              )}
            </div>
          )}

          {!canUsePublic && privateResults.length > 0 && (
            <p className="rounded-xl border border-dashed border-[var(--color-border)] px-3 py-3 text-xs text-[var(--color-text-secondary)]">
              公開推薦試用已用完。升級 Pro 可繼續從公開身份找商機。
              <Link href="/settings" className="ml-1 text-[var(--color-primary)]">
                去升級 →
              </Link>
            </p>
          )}

          {searchResult.briefing &&
            searchResult.briefing.scanned_count > searchResult.briefing.match_count && (
              <p className="px-2 pt-1 text-center text-xs leading-relaxed text-[var(--color-text-tertiary)]">
                其餘{" "}
                <span className="font-semibold text-[var(--color-text-secondary)]">
                  {searchResult.briefing.scanned_count - searchResult.briefing.match_count}
                </span>{" "}
                張，我判斷跟這個需求對不上，
                <span className="font-semibold text-[var(--color-text-secondary)]">沒有硬湊給你</span>。
              </p>
            )}
        </div>
      )}

      {searchResult?.status === "COMPLETED" && allResults.length === 0 && (
        <p className="rounded-xl border border-dashed border-[var(--color-border)] px-3 py-4 text-center text-sm text-[var(--color-text-secondary)]">
          搜尋完成，但這次沒有足夠吻合的人選（沒有硬湊結果）。
        </p>
      )}

      {searchResult?.status === "EMPTY" && searchResult.empty_state && (
        <SearchEmptyState state={searchResult.empty_state} />
      )}

      <PrivacyStrip className="text-center" />
      {showAha && <AhaMomentModal onClose={() => setShowAha(false)} />}
    </main>
  );
}
