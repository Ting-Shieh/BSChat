"use client";

import Link from "next/link";
import type { SearchQueryResponse, SearchResultItem } from "@/shared/types/search";
import { AssistantTurn } from "./AssistantTurn";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchResultCard } from "./SearchResultCard";

export function isPublicResult(item: SearchResultItem) {
  return item.source_pool === "public_directory";
}

export function isBrowseIntent(kind: string | null | undefined) {
  return kind === "browse_public" || kind === "browse_public_more";
}

/** Pending-only: skip the 5-step find_people plan while waiting on pool overview asks. */
export function looksLikeBrowseOverview(query: string) {
  const q = query.trim();
  if (!q) return false;
  if (/(列更多|再多|展開更多)/.test(q) && /公開/.test(q)) return true;
  return (
    /公開(商務|池|身份|推薦|名片|的人)/.test(q) &&
    /(有誰|有哪些|誰|列出|列表|名單|有沒有)/.test(q)
  );
}

function BrowsePublicSlot({ searchResult }: { searchResult: SearchQueryResponse }) {
  const pubs = (searchResult.results ?? []).filter(isPublicResult);
  return (
    <div className="flex flex-col gap-2">
      {pubs.map((item) => {
        const stub = item.stub_preview;
        if (!stub) return null;
        return (
          <div
            key={item.stub_id ?? `pub-${item.rank}`}
            className="rounded-xl border border-[var(--color-border)] bg-white px-3 py-2.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[var(--color-text-primary)]">
                  {stub.display_name}
                  {stub.company_name ? ` · ${stub.company_name}` : ""}
                </p>
                <p className="mt-0.5 text-[11px] text-[var(--color-text-tertiary)]">
                  {[stub.title, stub.product_keywords?.slice(0, 2).join("／")]
                    .filter(Boolean)
                    .join(" · ") || "公開身份樣例"}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-[var(--color-ai-bg)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-ai-text)]">
                公開
              </span>
            </div>
            {item.external_card_url && (
              <a
                href={item.external_card_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1.5 inline-block text-[11px] font-medium text-[var(--color-primary)]"
              >
                外部名片 →
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}

function FindPeopleSlot({
  searchResult,
  canUsePublic,
  poolCount,
}: {
  searchResult: SearchQueryResponse;
  canUsePublic: boolean;
  poolCount: number;
}) {
  const allResults = searchResult.results ?? [];
  const privateResults = allResults.filter((item) => !isPublicResult(item));
  const publicResults = allResults.filter(isPublicResult);

  return (
    <>
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
        </div>
      )}

      {privateResults.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-bold tracking-wide text-[var(--color-text-tertiary)]">
            你的名片庫 · 子團隊
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
    </>
  );
}

/**
 * Maps search `intent_kind` → AssistantTurn + content slot.
 * New non-find-people intents: add a slot here; keep the shell.
 */
export function SearchTurnReply({
  searchResult,
  canUsePublic,
  poolCount,
}: {
  searchResult: SearchQueryResponse;
  canUsePublic: boolean;
  poolCount: number;
}) {
  const allResults = searchResult.results ?? [];

  if (searchResult.status === "EMPTY" && searchResult.empty_state) {
    return <SearchEmptyState state={searchResult.empty_state} />;
  }

  if (searchResult.status === "COMPLETED" && allResults.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-[var(--color-border)] px-3 py-4 text-center text-sm text-[var(--color-text-secondary)]">
        搜尋完成，但這次沒有足夠吻合的人選（沒有硬湊結果）。
      </p>
    );
  }

  if (searchResult.status !== "COMPLETED" || allResults.length === 0) return null;

  if (isBrowseIntent(searchResult.intent_kind)) {
    return (
      <AssistantTurn
        layout="bubble"
        eyebrow={
          searchResult.intent_kind === "browse_public_more"
            ? "展開更多公開身份"
            : "這是「瀏覽公開池」"
        }
        message={searchResult.assistant_message}
      >
        <BrowsePublicSlot searchResult={searchResult} />
      </AssistantTurn>
    );
  }

  // find_people (default) — and future intents can branch above
  return (
    <AssistantTurn layout="stack" message={searchResult.assistant_message}>
      <FindPeopleSlot
        searchResult={searchResult}
        canUsePublic={canUsePublic}
        poolCount={poolCount}
      />
    </AssistantTurn>
  );
}
