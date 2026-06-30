"use client";

import type { SearchDebugInfo } from "@/shared/types/search";

function PoolSection({
  title,
  pool,
}: {
  title: string;
  pool: NonNullable<SearchDebugInfo["private"]>;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <p className="text-xs font-semibold text-[var(--color-text-primary)]">{title}</p>
      <dl className="mt-2 grid gap-1 text-[11px] text-[var(--color-text-secondary)]">
        <div className="flex flex-wrap gap-x-2">
          <dt className="text-[var(--color-text-tertiary)]">字面查詢</dt>
          <dd className="font-mono">{pool.lexical_query || "—"}</dd>
        </div>
        <div className="flex flex-wrap gap-x-2">
          <dt className="text-[var(--color-text-tertiary)]">語意向量</dt>
          <dd className="font-mono">{pool.semantic_query || "—"}</dd>
        </div>
        <div className="flex flex-wrap gap-x-3">
          <span>ts {pool.ts_hits}</span>
          <span>trgm +{pool.trgm_extra_hits}</span>
          <span>vector {pool.vector_hits}</span>
          {pool.widened && <span className="text-[var(--color-accent-hover)]">widened</span>}
        </div>
      </dl>
      {pool.top_candidates.length > 0 && (
        <ul className="mt-2 space-y-1 text-[11px]">
          {pool.top_candidates.map((c) => (
            <li
              key={c.id}
              className="flex items-baseline justify-between gap-2 font-mono text-[var(--color-text-secondary)]"
            >
              <span className="truncate">{c.label}</span>
              <span className="shrink-0 tabular-nums text-[var(--color-text-tertiary)]">
                {c.retrieval_score.toFixed(4)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function IntentBlock({ parsed }: { parsed: Record<string, unknown> }) {
  const entries = Object.entries(parsed).filter(
    ([, v]) => v != null && (Array.isArray(v) ? v.length > 0 : String(v).trim() !== ""),
  );
  if (entries.length === 0) {
    return <p className="text-[11px] text-[var(--color-text-tertiary)]">（無結構化 intent）</p>;
  }
  return (
    <dl className="grid gap-1 text-[11px]">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-wrap gap-x-2">
          <dt className="text-[var(--color-text-tertiary)]">{key}</dt>
          <dd className="font-mono text-[var(--color-text-secondary)]">
            {Array.isArray(value) ? value.join(", ") : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function SearchDebugPanel({ debug }: { debug: SearchDebugInfo }) {
  return (
    <details className="rounded-xl border border-dashed border-[var(--color-ai-border)] bg-[var(--color-ai-bg)]/40 p-3">
      <summary className="cursor-pointer select-none text-xs font-medium text-[var(--color-ai-text)]">
        開發 · 搜尋管線詳情
      </summary>
      <div className="mt-3 flex flex-col gap-3">
        <dl className="grid gap-1 text-[11px] text-[var(--color-text-secondary)]">
          <div className="flex flex-wrap gap-x-2">
            <dt className="text-[var(--color-text-tertiary)]">scope</dt>
            <dd>{debug.search_scope}</dd>
            <dt className="ml-2 text-[var(--color-text-tertiary)]">precision</dt>
            <dd>{debug.search_precision}</dd>
          </div>
          <div className="flex flex-wrap gap-x-2">
            <dt className="text-[var(--color-text-tertiary)]">intent</dt>
            <dd>{debug.intent_prompt_version}</dd>
            <dt className="ml-2 text-[var(--color-text-tertiary)]">rerank</dt>
            <dd>{debug.rerank_prompt_version}</dd>
          </div>
          <div className="flex flex-wrap gap-x-2">
            <dt className="text-[var(--color-text-tertiary)]">semantic_query</dt>
            <dd className="font-mono">{debug.semantic_query}</dd>
          </div>
          <div className="flex flex-wrap gap-x-3">
            <span>rerank 輸入 {debug.rerank_input_count}</span>
            <span>結果 {debug.result_count}</span>
            {debug.degraded && <span className="text-[var(--color-accent-hover)]">degraded</span>}
            {debug.latency_ms != null && <span>{debug.latency_ms}ms</span>}
          </div>
        </dl>

        <div>
          <p className="mb-1 text-[11px] font-semibold text-[var(--color-text-primary)]">Parsed intent</p>
          <IntentBlock parsed={debug.parsed_intent} />
        </div>

        {debug.private && <PoolSection title="私人池召回" pool={debug.private} />}
        {debug.public && <PoolSection title="公開池召回" pool={debug.public} />}
      </div>
    </details>
  );
}
