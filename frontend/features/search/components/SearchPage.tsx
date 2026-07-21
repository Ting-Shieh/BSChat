"use client";

import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import Link from "next/link";
import { useMe } from "@/features/auth/hooks";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import type { SearchQueryResponse } from "@/shared/types/search";
import {
  useLiveAugment,
  useSearch,
  useSearchSessionDetail,
  useSearchSessions,
  useSearchStatus,
} from "../hooks";
import { AhaMomentModal } from "./AhaMomentModal";
import { DegradedSearchBanner } from "./DegradedSearchBanner";
import { SearchDebugPanel } from "./SearchDebugPanel";
import { SearchInput } from "./SearchInput";
import { SearchPlanPanel } from "./SearchPlanPanel";
import {
  isBrowseIntent,
  looksLikeBrowseOverview,
  SearchTurnReply,
} from "./SearchTurnReply";

const AHA_KEY = "bschat-aha-shown";
const SHOW_SEARCH_DEBUG = process.env.NODE_ENV === "development";

type Turn = {
  query_text: string;
  response: SearchQueryResponse | null;
  pending?: boolean;
};

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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draftQuery, setDraftQuery] = useState("");
  const [planSession, setPlanSession] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const [showAha, setShowAha] = useState(false);
  const [loadSessionId, setLoadSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sessions = useSearchSessions(showHistory);
  const sessionDetail = useSearchSessionDetail(loadSessionId);

  const latest = turns[turns.length - 1];
  const latestResult = latest?.response ?? null;
  const liveAugment = useLiveAugment(latestResult?.query_id);

  useEffect(() => {
    if (latestResult?.aha_moment && !localStorage.getItem(AHA_KEY)) {
      setShowAha(true);
      localStorage.setItem(AHA_KEY, "1");
    }
  }, [latestResult?.aha_moment]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, search.isPending]);

  useEffect(() => {
    if (!sessionDetail.data) return;
    setSessionId(sessionDetail.data.id);
    setTurns(
      sessionDetail.data.turns.map((t) => ({
        query_text: t.query_text || "",
        response: t,
      })),
    );
    setLoadSessionId(null);
    setShowHistory(false);
  }, [sessionDetail.data]);

  const quotaZero = status ? status.quotas.search_cache_remaining_today <= 0 : false;
  const liveQuotaZero = status ? status.quotas.live_augment_remaining_month <= 0 : false;
  const inputDisabled = search.isPending || (status != null && (quotaZero || !status.can_search));
  const liveBusy = liveAugment.isPending;

  const browsePending =
    search.isPending && latest != null && looksLikeBrowseOverview(latest.query_text);
  const showPlan =
    !browsePending &&
    !isBrowseIntent(latestResult?.intent_kind) &&
    (search.isPending || (latest != null && latest.response != null));
  const planFinished =
    !search.isPending &&
    latestResult != null &&
    !isBrowseIntent(latestResult.intent_kind) &&
    (latestResult.status === "COMPLETED" || latestResult.status === "EMPTY");

  const followUps = useMemo(() => {
    const fromApi = latestResult?.follow_up_suggestions ?? [];
    if (fromApi.length) return fromApi;
    return [];
  }, [latestResult]);

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
    const text = q.trim();
    if (!text) return;
    setDraftQuery("");
    setTurns((prev) => [...prev, { query_text: text, response: null, pending: true }]);
    setPlanSession((n) => n + 1);
    search.mutate(
      { query_text: text, session_id: sessionId },
      {
        onSuccess: (data) => {
          if (data.session_id) setSessionId(data.session_id);
          setTurns((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.pending) {
              next[next.length - 1] = { query_text: text, response: data };
            } else {
              next.push({ query_text: text, response: data });
            }
            return next;
          });
        },
        onError: () => {
          setTurns((prev) => {
            const next = [...prev];
            if (next[next.length - 1]?.pending) next.pop();
            return next;
          });
        },
      },
    );
  };

  const startNewChat = () => {
    setSessionId(null);
    setTurns([]);
    setDraftQuery("");
    setPlanSession((n) => n + 1);
  };

  return (
    <main className="relative flex min-h-0 flex-1 flex-col">
      <div className="flex items-start justify-between gap-2 px-4 pb-2 pt-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">AI 搜尋</h1>
          <p className="text-sm text-[var(--color-text-secondary)]">{statusLine()}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setShowHistory(true)}
            className="rounded-lg bg-[var(--color-primary-muted)] px-2.5 py-1.5 text-xs font-semibold text-[var(--color-primary)]"
          >
            紀錄
          </button>
          {turns.length > 0 && (
            <button
              type="button"
              onClick={startNewChat}
              className="rounded-lg border border-[var(--color-border)] px-2.5 py-1.5 text-xs text-[var(--color-text-secondary)]"
            >
              新對話
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 pb-4">
      {statusError && (
        <p className="text-xs text-[var(--color-accent-hover)]">無法載入搜尋狀態，仍可直接搜尋。</p>
      )}

      {quotaZero && (
        <p className="text-xs text-[var(--color-accent-hover)]">今日搜尋額度已用完，明天再試。</p>
      )}

      {!statusLoading && status && !status.can_search && turns.length === 0 && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-4 text-center text-sm text-[var(--color-text-secondary)]">
          先收錄幾張名片建立索引
          <Link href="/capture" className="mt-2 block text-[var(--color-primary)]">
            去收錄 →
          </Link>
        </div>
      )}

      {turns.length === 0 && (
        <p className="text-center text-xs text-[var(--color-text-tertiary)]">
          可問「公開商務有誰」瀏覽公開池，或描述你要找的產品／職稱。同一串可追問。
        </p>
      )}

      {turns.map((turn, idx) => {
        const isLast = idx === turns.length - 1;
        return (
          <div key={`${turn.query_text}-${idx}`} className="flex flex-col gap-3">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--color-primary)] px-3.5 py-2.5 text-[14px] leading-relaxed text-white">
                {turn.query_text}
              </div>
            </div>

            {isLast && showPlan && (
              <SearchPlanPanel
                key={planSession}
                running={search.isPending}
                finished={planFinished}
                includePublicPool={includePublicPool}
                publicSkipReason={publicSkipReason}
                indexedHint={status?.indexed_count}
              />
            )}

            {isLast && search.isPending && (
              <p className="animate-pulse text-center text-xs text-[var(--color-text-tertiary)]">
                {browsePending
                  ? "正在瀏覽公開池樣例…"
                  : "正在向伺服器搜尋（含 AI 排序），請勿關閉頁面…"}
              </p>
            )}

            {turn.response && (
              <SearchTurnReply
                searchResult={turn.response}
                canUsePublic={canUsePublic}
                poolCount={poolCount}
              />
            )}
          </div>
        );
      })}

      {search.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
          搜尋失敗（後端逾時或連線中斷）。請再送一次。
        </div>
      )}

      {isLastTurnLive(latestResult, liveQuotaZero, liveBusy, liveAugment, status, setTurns)}

      {latestResult?.debug && SHOW_SEARCH_DEBUG && <SearchDebugPanel debug={latestResult.debug} />}

      {latestResult?.status === "COMPLETED" && latestResult.degraded && (latestResult.results?.length ?? 0) > 0 && (
        <DegradedSearchBanner />
      )}

      {followUps.length > 0 && !search.isPending && (
        <div className="flex flex-wrap gap-2">
          {followUps.map((s) => (
            <button
              key={s}
              type="button"
              disabled={inputDisabled}
              onClick={() => handleSearch(s)}
              className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[11.5px] text-[var(--color-text-secondary)]"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div ref={bottomRef} />
      <PrivacyStrip className="text-center" />
      </div>

      <div className="shrink-0 border-t border-[var(--color-border)]/60 bg-[var(--color-bg)] px-3 pb-3 pt-2">
        <SearchInput
          disabled={inputDisabled}
          suggestions={status?.sample_queries ?? []}
          showSuggestions={turns.length === 0}
          value={draftQuery}
          onValueChange={setDraftQuery}
          onSubmit={handleSearch}
          placeholder={turns.length === 0 ? "用一句話描述你要找的人…" : "追問或開新搜尋…"}
          submitLabel="送出"
        />
      </div>

      {showAha && <AhaMomentModal onClose={() => setShowAha(false)} />}

      {showHistory && (
        <div
          className="fixed inset-0 z-40 flex items-end bg-black/35 sm:items-center sm:justify-center"
          onClick={() => setShowHistory(false)}
        >
          <div
            className="max-h-[78vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-[var(--color-surface)] p-4 sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-base font-semibold text-[var(--color-text-primary)]">對話紀錄</p>
                <p className="text-[11px] text-[var(--color-text-tertiary)]">點開可回看上次問什麼</p>
              </div>
              <button
                type="button"
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[#F5F5F4] text-lg"
                onClick={() => setShowHistory(false)}
              >
                ×
              </button>
            </div>
            {sessions.isLoading && (
              <p className="text-xs text-[var(--color-text-secondary)]">載入中…</p>
            )}
            {(sessions.data?.items ?? []).length === 0 && !sessions.isLoading && (
              <p className="text-sm text-[var(--color-text-secondary)]">尚無對話紀錄</p>
            )}
            <ul className="space-y-2">
              {(sessions.data?.items ?? []).map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className="w-full rounded-xl border border-[var(--color-border)] px-3 py-2.5 text-left hover:border-[var(--color-primary)]"
                    onClick={() => setLoadSessionId(s.id)}
                  >
                    <p className="truncate text-sm font-medium text-[var(--color-text-primary)]">
                      {s.title}
                    </p>
                    <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">
                      {new Date(s.updated_at).toLocaleString()} · {s.turn_count} 則
                    </p>
                  </button>
                </li>
              ))}
            </ul>
            {sessionDetail.isLoading && (
              <p className="mt-2 text-xs text-[var(--color-text-secondary)]">開啟對話中…</p>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

function isLastTurnLive(
  latestResult: SearchQueryResponse | null,
  liveQuotaZero: boolean,
  liveBusy: boolean,
  liveAugment: ReturnType<typeof useLiveAugment>,
  status: ReturnType<typeof useSearchStatus>["data"],
  setTurns: Dispatch<SetStateAction<Turn[]>>,
) {
  if (!latestResult?.suggest_live) return null;
  if (liveQuotaZero) {
    return (
      <p className="text-xs text-[var(--color-text-secondary)]">
        本月即時查詢額度已用完（{status?.quotas.live_augment_remaining_month ?? 0} 次）。
      </p>
    );
  }
  return (
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
            onSuccess: (data) => {
              setTurns((prev) => {
                if (!prev.length) return prev;
                const next = [...prev];
                next[next.length - 1] = {
                  ...next[next.length - 1],
                  response: data,
                };
                return next;
              });
            },
          })
        }
        className="mt-3 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {liveBusy ? "查詢中…" : "即時查詢"}
      </button>
    </div>
  );
}
