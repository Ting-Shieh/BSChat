"use client";

import type { CompanyEnrichmentSection } from "@/shared/types/contact";

type Props = {
  enrichment: CompanyEnrichmentSection;
  companyId?: string | null;
  onRefresh?: () => void;
  refreshPending?: boolean;
  refreshError?: string | null;
};

export function CompanyEnrichmentBlock({
  enrichment,
  companyId,
  onRefresh,
  refreshPending,
  refreshError,
}: Props) {
  if (enrichment.status === "hidden") {
    return null;
  }

  const refreshButton =
    enrichment.can_refresh && companyId && onRefresh ? (
      <button
        type="button"
        onClick={onRefresh}
        disabled={refreshPending}
        className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)] disabled:opacity-50"
      >
        {refreshPending ? "更新中…" : "更新公司資訊"}
        {enrichment.refresh_quota_remaining != null && enrichment.refresh_quota_remaining >= 0
          ? `（本月剩 ${enrichment.refresh_quota_remaining} 次）`
          : ""}
      </button>
    ) : null;

  if (enrichment.status === "pending") {
    return (
      <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
        <h2 className="mb-2 text-sm font-medium text-[var(--color-ai-text)]">公司補全</h2>
        <p className="animate-pulse text-sm text-[var(--color-text-secondary)]">⏳ 正在補充公司資訊…</p>
      </section>
    );
  }

  if (enrichment.status === "failed") {
    return (
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="mb-2 text-sm font-medium text-[var(--color-text-secondary)]">公司補全</h2>
        <p className="text-sm text-[var(--color-text-tertiary)]">無法取得公開資訊，可稍後再試或確認公司名稱。</p>
        {refreshButton}
        {refreshError && (
          <p className="mt-2 text-xs text-[var(--color-accent-hover)]">{refreshError}</p>
        )}
      </section>
    );
  }

  if (enrichment.status === "rejected") {
    return (
      <section className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="mb-1 text-sm font-medium text-[var(--color-text-secondary)]">公司補全</h2>
        <p className="text-xs text-[var(--color-text-tertiary)]">已隱藏 AI 補全內容</p>
        {refreshButton}
      </section>
    );
  }

  const products = enrichment.main_products ?? [];

  return (
    <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-[var(--color-ai-text)]">公司補全</h2>
        {enrichment.status === "partial" && (
          <span className="rounded bg-[var(--color-accent-muted)] px-1.5 py-0.5 text-[10px] text-[var(--color-accent-hover)]">
            資訊不足
          </span>
        )}
      </div>

      {products.length > 0 ? (
        <ul className="mb-2 list-inside list-disc space-y-1 text-sm text-[var(--color-text-primary)]">
          {products.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--color-text-secondary)]">尚無產品資訊</p>
      )}

      {enrichment.website_url && (
        <a
          href={enrichment.website_url.startsWith("http") ? enrichment.website_url : `https://${enrichment.website_url}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[var(--color-primary)] underline"
        >
          {enrichment.website_url}
        </a>
      )}

      {enrichment.provenance_label && (
        <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">{enrichment.provenance_label}</p>
      )}

      {refreshButton}
      {refreshError && (
        <p className="mt-2 text-xs text-[var(--color-accent-hover)]">{refreshError}</p>
      )}
    </section>
  );
}
