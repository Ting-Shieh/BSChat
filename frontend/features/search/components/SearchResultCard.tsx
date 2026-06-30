"use client";

import Link from "next/link";
import { useCopyContact, CopyToast } from "@/features/actions";
import { ContactPreviewCard } from "@/shared/components/ContactPreviewCard";
import type { SearchResultItem } from "@/shared/types/search";

const MATCH_FIELD_LABELS: Record<string, string> = {
  company_name: "公司",
  title: "職稱",
  company_products: "產品",
  responsibility_scope: "職責",
  source_label: "來源",
};

function MatchSourceChips({ sources }: { sources: SearchResultItem["match_sources"] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {sources.map((src, i) => (
        <span
          key={`${src.field}-${i}`}
          className="inline-block rounded bg-[var(--color-bg)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-secondary)]"
        >
          {MATCH_FIELD_LABELS[src.field] ?? src.field}：{src.value}
        </span>
      ))}
    </div>
  );
}

export function SearchResultCard({
  item,
  queryId,
}: {
  item: SearchResultItem;
  queryId: string;
}) {
  const { copy, message } = useCopyContact();
  const isPublic = item.source_pool === "public_directory" && item.stub_preview;

  if (isPublic) {
    const stub = item.stub_preview!;
    return (
      <article className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="inline-block rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-800">
              公開商務 · {item.publisher_org_name ?? stub.company_name}
            </span>
            <p className="mt-2 text-sm font-medium text-[var(--color-text-primary)]">{stub.display_name}</p>
            <p className="text-xs text-[var(--color-text-secondary)]">
              {stub.company_name}
              {stub.title ? ` · ${stub.title}` : ""}
            </p>
            {stub.product_keywords.length > 0 && (
              <p className="mt-1 text-[10px] text-[var(--color-text-tertiary)]">
                {stub.product_keywords.join(" · ")}
              </p>
            )}
          </div>
        </div>
        <p className="mt-3 rounded-lg bg-[var(--color-ai-bg)] px-3 py-2 text-sm text-[var(--color-ai-text)]">
          {item.match_reason}
        </p>
        <MatchSourceChips sources={item.match_sources} />
        {item.external_card_url && (
          <a
            href={item.external_card_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-block rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)]"
          >
            前往外部名片
          </a>
        )}
      </article>
    );
  }

  const preview = item.contact_preview;
  if (!preview || !item.contact_id) return null;

  const phone = preview.phones[0];
  const email = preview.emails[0];

  return (
    <article className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <span className="inline-block rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-800">
        你的名片庫
      </span>
      <Link href={`/contacts/${item.contact_id}?from_search=${queryId}&rank=${item.rank}`} className="mt-2 block">
        <div className="relative">
          <ContactPreviewCard preview={preview} />
          {preview.review_status === "unconfirmed" && (
            <span className="absolute right-0 top-0 rounded bg-[var(--color-accent-muted)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-accent-hover)]">
              未確認
            </span>
          )}
        </div>
      </Link>

      {(phone || email) && (
        <div className="mt-2 space-y-1 text-xs text-[var(--color-text-secondary)]">
          {phone && <p>📞 {phone}</p>}
          {email && <p>✉️ {email}</p>}
        </div>
      )}

      <p className="mt-3 rounded-lg bg-[var(--color-ai-bg)] px-3 py-2 text-sm text-[var(--color-ai-text)]">
        {item.match_reason}
        {item.live_products && item.live_products.length > 0 && (
          <span className="ml-2 inline-block rounded bg-[var(--color-surface)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-primary)]">
            即時查詢
          </span>
        )}
      </p>
      <MatchSourceChips sources={item.match_sources} />

      {(phone || email) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {phone && (
            <button
              type="button"
              onClick={() => void copy(phone, "電話")}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
              aria-label={`複製 ${preview.display_name ?? "聯絡人"} 的電話`}
            >
              📋 複製電話
            </button>
          )}
          {email && (
            <button
              type="button"
              onClick={() => void copy(email, "Email")}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
              aria-label={`複製 ${preview.display_name ?? "聯絡人"} 的 Email`}
            >
              ✉️ 複製 Email
            </button>
          )}
          {message && (
            <span className="text-xs text-[var(--color-accent-hover)]" role="status">
              {message}
            </span>
          )}
        </div>
      )}
      <CopyToast message={message} />
    </article>
  );
}
