"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCopyContact, CopyToast } from "@/features/actions";
import { useAuthStore } from "@/features/auth/store";
import { CompanyEnrichmentBlock } from "@/features/enrichment";
import { PersonEnrichBlock } from "@/features/person-enrich";
import { useReEnrichCompany } from "@/features/enrichment/hooks";
import { SearchContextBanner, useSearchResultContext } from "@/features/search";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import type { ContactDetail } from "@/shared/types/contact";
import { ContactEditSheet } from "./ContactEditSheet";
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
  const reEnrich = useReEnrichCompany(contact.id);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [localContact, setLocalContact] = useState(contact);

  useEffect(() => {
    setLocalContact(contact);
  }, [contact]);

  const saveEdit = useMutation({
    mutationFn: (fields: contactsApi.ContactUpdateFields) =>
      contactsApi.updateContact(token!, localContact.id, {
        version: localContact.version,
        fields,
      }),
    onSuccess: (updated) => {
      setLocalContact(updated);
      setEditOpen(false);
      setEditError(null);
      queryClient.setQueryData(["contact", contact.id], updated);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "儲存失敗";
      if (msg.includes("CONTACT_VERSION_CONFLICT")) {
        setEditError("資料已被更新，請關閉後重新整理再編輯");
      } else {
        setEditError("無法儲存，請稍後再試");
      }
    },
  });

  const handleRefreshCompany = () => {
    if (!localContact.company_id) return;
    setRefreshError(null);
    reEnrich.mutate(
      { companyId: localContact.company_id },
      {
        onError: (err) => {
          const msg = err instanceof Error ? err.message : "更新失敗";
          if (msg.includes("MANUAL_REFRESH_QUOTA_EXCEEDED")) {
            setRefreshError("本月手動更新次數已用完");
          } else if (msg.includes("ENRICH_IN_PROGRESS")) {
            setRefreshError("公司資訊正在更新中");
          } else {
            setRefreshError("無法更新公司資訊，請稍後再試");
          }
        },
      },
    );
  };

  const remove = useMutation({
    mutationFn: () => contactsApi.deleteContact(token!, contact.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      router.push("/contacts");
    },
  });

  const original = localContact.sections.card_original;
  const ai = localContact.sections.ai_inferred.responsibility_scope;
  const personEnrich = localContact.sections.ai_inferred.person_enrich;
  const phone = localContact.phones?.[0]?.value;
  const email = localContact.emails?.[0]?.value;

  return (
    <main className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <Link href="/contacts" className="text-sm text-[var(--color-primary)]">
          ← 名片庫
        </Link>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setEditError(null);
              setEditOpen(true);
            }}
            className="text-xs font-medium text-[var(--color-primary)]"
          >
            編輯
          </button>
          <button
            type="button"
            onClick={() => remove.mutate()}
            disabled={remove.isPending}
            className="text-xs text-[var(--color-error)]"
          >
            刪除
          </button>
        </div>
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

      {personEnrich && (
        <PersonEnrichBlock
          contactId={localContact.id}
          section={personEnrich}
          version={localContact.version}
          hasLinkedIn={Boolean(localContact.linkedin_url?.trim())}
          onContactUpdated={(updated) => {
            setLocalContact(updated);
            queryClient.setQueryData(["contacts", contact.id, token], updated);
          }}
          onAddLinkedIn={() => {
            setEditError(null);
            setEditOpen(true);
          }}
        />
      )}

      {ai && (
        <details className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
          <summary className="cursor-pointer text-sm font-medium text-[var(--color-text-secondary)]">
            系統參考（名片推估）
          </summary>
          <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-tertiary)]">
            {String(ai.value)}
          </p>
          <p className="mt-2 text-[10px] text-[var(--color-text-tertiary)]">
            僅供對照，與上方「職責理解」來源不同。
          </p>
        </details>
      )}

      <CompanyEnrichmentBlock
        enrichment={localContact.sections.company_enrichment}
        companyId={localContact.company_id}
        onRefresh={localContact.company_id ? handleRefreshCompany : undefined}
        refreshPending={reEnrich.isPending}
        refreshError={refreshError}
      />

      {localContact.source_label && (
        <p className="text-center text-xs text-[var(--color-text-tertiary)]">
          來源：{localContact.source_label}
        </p>
      )}
      <PrivacyStrip className="text-center" />
      <CopyToast message={message} />

      <ContactEditSheet
        contact={localContact}
        open={editOpen}
        saving={saveEdit.isPending}
        error={editError}
        onClose={() => setEditOpen(false)}
        onSave={(fields) => saveEdit.mutate(fields)}
      />
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
