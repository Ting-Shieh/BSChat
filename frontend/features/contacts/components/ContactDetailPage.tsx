"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCopyContact, CopyToast } from "@/features/actions";
import { useAuthStore } from "@/features/auth/store";
import { CompanyEnrichmentBlock } from "@/features/enrichment";
import { SearchContextBanner, useSearchResultContext } from "@/features/search";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import type { ContactDetail } from "@/shared/types/contact";
import * as contactsApi from "../api";

export function ContactDetailPage({
  contact,
  fromSearch,
  searchRank,
}: {
  contact: ContactDetail;
  fromSearch?: string | null;
  searchRank?: string | null;
}) {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { copy, message } = useCopyContact();
  const { data: searchContext } = useSearchResultContext(fromSearch, contact.id);

  const remove = useMutation({
    mutationFn: () => contactsApi.deleteContact(token!, contact.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      router.push("/contacts");
    },
  });

  const original = contact.sections.card_original;
  const ai = contact.sections.ai_inferred.responsibility_scope;
  const phone = contact.phones?.[0]?.value;
  const email = contact.emails?.[0]?.value;

  return (
    <main className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <Link href="/contacts" className="text-sm text-[var(--color-primary)]">
          ← 名片庫
        </Link>
        <button
          type="button"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
          className="text-xs text-[var(--color-error)]"
        >
          刪除
        </button>
      </div>

      {fromSearch && (
        <SearchContextBanner
          matchReason={searchContext?.match_reason}
          matchSources={searchContext?.match_sources}
          rank={searchRank ?? undefined}
        />
      )}

      {original.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={original.image_url}
          alt="名片"
          className="mx-auto max-h-48 rounded-lg border border-[var(--color-border)] object-contain"
        />
      )}

      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--color-text-primary)]">名片原文（OCR）</h2>
        <dl className="space-y-2">
          {original.fields.map((f) => (
            <div key={f.name}>
              <dt className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                <ConfidenceDot confidence={f.confidence ?? 1} />
                {label(f.name)}
              </dt>
              <dd className="text-sm text-[var(--color-text-primary)]">{f.value ?? "—"}</dd>
            </div>
          ))}
        </dl>
      </section>

      {(phone || email) && (
        <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h2 className="mb-2 text-sm font-medium text-[var(--color-text-primary)]">聯絡方式</h2>
          {phone && <p className="text-sm text-[var(--color-text-secondary)]">📞 {phone}</p>}
          {email && <p className="text-sm text-[var(--color-text-secondary)]">✉️ {email}</p>}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {phone && (
              <button
                type="button"
                onClick={() => void copy(phone, "電話")}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
              >
                📋 複製電話
              </button>
            )}
            {email && (
              <button
                type="button"
                onClick={() => void copy(email, "Email")}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
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
        </section>
      )}

      {ai && (
        <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
          <h2 className="mb-2 text-sm font-medium text-[var(--color-ai-text)]">AI 推估職責</h2>
          <p className="text-sm text-[var(--color-text-primary)]">{String(ai.value)}</p>
        </section>
      )}

      <CompanyEnrichmentBlock enrichment={contact.sections.company_enrichment} />

      {contact.source_label && (
        <p className="text-center text-xs text-[var(--color-text-tertiary)]">來源：{contact.source_label}</p>
      )}
      <PrivacyStrip className="text-center" />
      <CopyToast message={message} />
    </main>
  );
}

function label(name: string) {
  const map: Record<string, string> = {
    name: "姓名",
    company: "公司",
    title: "抬頭",
    address: "地址",
    website: "網站",
  };
  return map[name] ?? name;
}
