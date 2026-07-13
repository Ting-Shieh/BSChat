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
import { resolveMediaUrl } from "@/shared/lib/media-url";
import type { ContactDetail } from "@/shared/types/contact";
import { ContactEditSheet } from "./ContactEditSheet";
import * as contactsApi from "../api";

const DORMANT_THRESHOLD = 6;

function dormantMonths(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const created = new Date(iso);
  if (Number.isNaN(created.getTime())) return null;
  const days = Math.floor((Date.now() - created.getTime()) / 86_400_000);
  if (days < 0) return null;
  return Math.floor(days / 30);
}

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
  const [noteDraft, setNoteDraft] = useState(contact.personal_note ?? "");

  useEffect(() => {
    setLocalContact(contact);
    setNoteDraft(contact.personal_note ?? "");
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

  const saveNote = useMutation({
    mutationFn: () =>
      contactsApi.updateContact(token!, localContact.id, {
        version: localContact.version,
        fields: { personal_note: noteDraft.trim() },
      }),
    onSuccess: (updated) => {
      setLocalContact(updated);
      queryClient.setQueryData(["contacts", contact.id, token], updated);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => contactsApi.deleteContact(token!, contact.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      router.push("/contacts");
    },
  });

  const original = localContact.sections.card_original;
  const cardImageSrc = resolveMediaUrl(original.image_url);
  const ai = localContact.sections.ai_inferred.responsibility_scope;
  const personEnrich = localContact.sections.ai_inferred.person_enrich;
  const phone = localContact.phones?.[0]?.value;
  const email = localContact.emails?.[0]?.value;
  const dormant = dormantMonths(localContact.created_at);
  const isDormant = dormant !== null && dormant >= DORMANT_THRESHOLD;
  const initials = (localContact.display_name ?? localContact.company_name ?? "?").slice(0, 2);

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

      {/* Header — name + chips */}
      <div className="flex gap-3">
        {cardImageSrc ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cardImageSrc}
            alt=""
            className="h-[52px] w-[52px] shrink-0 rounded-[12px] border border-[var(--color-border)] object-cover"
          />
        ) : (
          <div className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-[12px] bg-[var(--color-primary-muted)] text-base font-bold text-[var(--color-primary)]">
            {initials}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-[19px] font-semibold text-[var(--color-text-primary)]">
            {localContact.display_name ?? "未命名"}
          </h1>
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            {[localContact.company_name, localContact.title].filter(Boolean).join(" · ") || "—"}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {isDormant && (
              <span className="rounded-full bg-[var(--color-accent-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-accent-hover)]">
                💤 沉睡 {dormant} 個月
              </span>
            )}
            {localContact.captured_by_name && (
              <span className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[10px] text-[var(--color-text-secondary)]">
                👤 由 {localContact.captured_by_name} 收錄
              </span>
            )}
            {localContact.review_status === "unconfirmed" && (
              <span className="rounded-full bg-[var(--color-accent-muted)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-accent-hover)]">
                待確認
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      {(phone || email) && (
        <div className="flex gap-2">
          {phone && (
            <a
              href={`tel:${phone}`}
              className="flex-1 rounded-lg bg-[var(--color-primary)] py-2.5 text-center text-[13px] font-semibold text-white"
            >
              撥號
            </a>
          )}
          {email && (
            <a
              href={`mailto:${email}`}
              className="flex-1 rounded-lg border-[1.5px] border-[var(--color-primary)] bg-[var(--color-surface)] py-2.5 text-center text-[13px] font-semibold text-[var(--color-primary)]"
            >
              Email
            </a>
          )}
          <button
            type="button"
            onClick={() => void copy(phone || email || "", phone ? "電話" : "Email")}
            className="flex-1 rounded-lg border-[1.5px] border-[var(--color-primary)] bg-[var(--color-surface)] py-2.5 text-center text-[13px] font-semibold text-[var(--color-primary)]"
          >
            複製
          </button>
        </div>
      )}

      {/* ① 名片原文 */}
      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        ① 名片原文（你收到的）
      </p>
      <section className="-mt-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
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
        {(phone || email) && (
          <div className="mt-3 space-y-1 border-t border-[var(--color-border)] pt-3 text-sm text-[var(--color-text-secondary)]">
            {phone && <p>📞 {phone}</p>}
            {email && <p>✉️ {email}</p>}
          </div>
        )}
      </section>

      {/* ② AI 看懂公司 */}
      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        ② AI 看懂公司
      </p>
      <div className="-mt-2">
        <CompanyEnrichmentBlock
          enrichment={localContact.sections.company_enrichment}
          companyId={localContact.company_id}
          onRefresh={localContact.company_id ? handleRefreshCompany : undefined}
          refreshPending={reEnrich.isPending}
          refreshError={refreshError}
        />
      </div>

      {/* ③ AI 推估職責 */}
      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        ③ AI 推估個人負責
      </p>
      {personEnrich && (
        <div className="-mt-2">
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
        </div>
      )}
      {ai && (
        <div className="-mt-2 border-l-[3px] border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] px-3 py-3">
          <p className="text-sm leading-relaxed text-[var(--color-text-primary)]">{String(ai.value)}</p>
          <span className="mt-2 inline-block rounded-full bg-[var(--color-accent-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-accent-hover)]">
            ✦ AI 推估 · 僅供參考
          </span>
        </div>
      )}
      {!personEnrich && !ai && (
        <p className="-mt-2 text-sm text-[var(--color-text-tertiary)]">尚未有職責推估</p>
      )}

      {/* 人工備註 */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">📝 我的備註</h2>
          <span className="text-[10px] text-[var(--color-text-tertiary)]">AI 不會動</span>
        </div>
        <textarea
          value={noteDraft}
          onChange={(e) => setNoteDraft(e.target.value)}
          rows={3}
          placeholder="記下只有人才知道的事：喜好、關係、提醒（例：愛喝手沖、忌辣、上次談到擴廠）"
          className="w-full resize-none rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]"
        />
        <div className="mt-2 flex items-center gap-3">
          <button
            type="button"
            onClick={() => saveNote.mutate()}
            disabled={saveNote.isPending || noteDraft === (localContact.personal_note ?? "")}
            className="rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-40"
          >
            {saveNote.isPending ? "儲存中…" : "儲存備註"}
          </button>
          {!saveNote.isPending &&
            noteDraft === (localContact.personal_note ?? "") &&
            (localContact.personal_note ?? "") !== "" && (
              <span className="text-xs text-[var(--color-success)]" role="status">
                已儲存 ✓
              </span>
            )}
          {saveNote.isError && (
            <span className="text-xs text-[var(--color-error)]">儲存失敗，請稍後再試</span>
          )}
        </div>
      </section>

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
