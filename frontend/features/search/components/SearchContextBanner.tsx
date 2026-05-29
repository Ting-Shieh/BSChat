"use client";

import type { MatchSource } from "@/shared/types/search";

const FIELD_LABELS: Record<string, string> = {
  title: "職稱",
  company_name: "公司",
  company_products: "產品",
  responsibility_scope: "職責",
  source_label: "場合",
};

export function SearchContextBanner({
  matchReason,
  matchSources = [],
  rank,
}: {
  matchReason?: string | null;
  matchSources?: MatchSource[];
  rank?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] px-3 py-3 text-sm text-[var(--color-ai-text)]">
      <p className="text-xs font-medium">
        來自 AI 搜尋結果
        {rank ? ` · 第 ${rank} 名` : ""}
      </p>
      {matchReason && (
        <p className="mt-2 text-sm text-[var(--color-text-primary)]">{matchReason}</p>
      )}
      {matchSources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {matchSources.map((source) => (
            <span
              key={`${source.field}-${source.value}`}
              className="rounded-full border border-[var(--color-ai-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[11px] text-[var(--color-text-secondary)]"
            >
              {FIELD_LABELS[source.field] ?? source.field}：{source.value}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
