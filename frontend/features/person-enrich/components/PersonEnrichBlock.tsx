"use client";

import { FormEvent, useRef, useState } from "react";
import type { ContactDetail } from "@/shared/types/contact";
import type { PersonEnrichSection } from "@/shared/types/contact";
import { cn } from "@/shared/lib/cn";
import { usePersonEnrichMutations } from "../hooks";

const UPGRADE_MAIL =
  "mailto:hello@bschat.app?subject=" + encodeURIComponent("申請升級 BSChat Pro");

const MAX_LEN = 500;

type Props = {
  contactId: string;
  section: PersonEnrichSection;
  version: number;
  hasLinkedIn?: boolean;
  /** 無 LinkedIn 時引導使用者去填 */
  onAddLinkedIn?: () => void;
  onContactUpdated?: (contact: ContactDetail) => void;
};

function sourceChip(dataSource: string | null | undefined, provenance?: string | null) {
  if (dataSource === "user_manual") {
    return { label: "使用者筆記", className: "bg-[var(--color-surface)] text-[var(--color-text-secondary)]" };
  }
  if (dataSource === "linkedin_profile" || dataSource === "linkedin_search") {
    return { label: "LinkedIn", className: "bg-[var(--color-ai-bg)] text-[var(--color-ai-text)]" };
  }
  if (dataSource === "linkedin_url_public") {
    return { label: "公開摘要", className: "bg-[var(--color-surface)] text-[var(--color-text-secondary)]" };
  }
  if (dataSource === "card_inference") {
    return { label: "名片推估", className: "bg-[var(--color-surface)] text-[var(--color-text-tertiary)]" };
  }
  if (provenance?.includes("使用者")) {
    return { label: "使用者筆記", className: "bg-[var(--color-surface)] text-[var(--color-text-secondary)]" };
  }
  return null;
}

export function PersonEnrichBlock({
  contactId,
  section,
  version,
  hasLinkedIn = section.has_linkedin_url,
  onAddLinkedIn,
  onContactUpdated,
}: Props) {
  const { enrich, confirm, reject, saveScope } = usePersonEnrichMutations(contactId);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const linkedInLock = useRef(false);

  const busy =
    enrich.isPending || confirm.isPending || reject.isPending || saveScope.isPending;

  const linkedInBusy = busy || section.status === "pending" || linkedInLock.current;

  const hasContent = Boolean(section.person_scope?.trim());
  const isEmpty =
    !hasContent &&
    (section.status === "never" ||
      section.status === "insufficient" ||
      section.status === "rejected");
  const chip = sourceChip(section.data_source, section.provenance_label);
  const showInsufficientNote = section.status === "insufficient";

  const handleScopeSaved = (updated: ContactDetail) => {
    onContactUpdated?.(updated);
    setEditing(false);
    setError(null);
  };

  const runLinkedInUpdate = () => {
    if (linkedInBusy || section.can_enrich === false) return;
    if (!hasLinkedIn) {
      onAddLinkedIn?.();
      return;
    }
    if (linkedInLock.current) return;
    linkedInLock.current = true;
    setError(null);
    enrich.mutate(undefined, {
      onError: (err) => setError(formatError(err)),
      onSettled: () => {
        linkedInLock.current = false;
      },
    });
  };

  const startInlineEdit = () => {
    setDraft(section.person_scope ?? "");
    setEditing(true);
    setError(null);
  };

  const saveInline = (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    const scope = text.startsWith("可能負責") ? text : `可能負責${text}`;
    saveScope.mutate(
      { version, person_scope: scope },
      {
        onSuccess: handleScopeSaved,
        onError: (err) => setError(formatScopeError(err)),
      },
    );
  };

  const clearContent = () => {
    setError(null);
    if (section.data_source === "user_manual") {
      saveScope.mutate(
        { version, person_scope: "" },
        {
          onSuccess: handleScopeSaved,
          onError: (err) => setError(formatScopeError(err)),
        },
      );
      return;
    }
    reject.mutate(undefined, { onError: (err) => setError(formatError(err)) });
  };

  if (section.status === "locked") {
    return (
      <section className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">職責理解</h2>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Pro 可從 LinkedIn 公開資料更新職責範圍，並標示來源。
        </p>
        <a
          href={UPGRADE_MAIL}
          className="mt-4 block w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-center text-sm font-medium text-white"
        >
          聯絡我們升級 Pro
        </a>
      </section>
    );
  }

  if (section.status === "pending") {
    return (
      <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-ai-text)]">職責理解</h2>
        <p className="mt-3 animate-pulse text-sm text-[var(--color-text-secondary)]">
          {busy ? "正在查公開摘要並整理…" : "正在從 LinkedIn 整理…"}
        </p>
        <p className="mt-2 text-[10px] text-[var(--color-text-tertiary)]">
          通常需 10–60 秒；若超過 2 分鐘仍無結果，請重新整理頁面再試。
        </p>
      </section>
    );
  }

  if (section.status === "needs_confirmation" && section.candidates?.length) {
    if (editing) {
      return (
        <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
          <h2 className="text-sm font-medium text-[var(--color-ai-text)]">職責理解</h2>
          <form onSubmit={saveInline} className="mt-3">
            <label className="block text-xs text-[var(--color-text-secondary)]">
              可能負責的業務範圍（儲存後標示為使用者筆記）
            </label>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, MAX_LEN))}
              rows={4}
              className="mt-1 w-full resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]"
              autoFocus
              required
            />
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="flex-1 rounded-lg border border-[var(--color-border)] py-2 text-sm text-[var(--color-text-secondary)]"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={!draft.trim() || saveScope.isPending}
                className="flex-1 rounded-lg bg-[var(--color-primary)] py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {saveScope.isPending ? "儲存中…" : "儲存"}
              </button>
            </div>
          </form>
          {error && <p className="mt-2 text-xs text-[var(--color-accent-hover)]">{error}</p>}
        </section>
      );
    }

    return (
      <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-ai-text)]">職責理解</h2>
        <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">請確認是否為同一人</p>
        <ul className="mt-3 space-y-2">
          {section.candidates.map((c) => (
            <li key={c.index}>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setError(null);
                  confirm.mutate(c.index, { onError: (err) => setError(formatError(err)) });
                }}
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-left text-sm hover:border-[var(--color-primary)] disabled:opacity-50"
              >
                <span className="font-medium">{c.headline || "LinkedIn 候選"}</span>
                {c.linkedin_url && (
                  <span className="mt-1 block truncate text-xs text-[var(--color-text-tertiary)]">
                    {c.linkedin_url}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          disabled={busy}
          onClick={startInlineEdit}
          className="mt-3 text-xs text-[var(--color-text-tertiary)] underline-offset-2 hover:text-[var(--color-primary)] hover:underline"
        >
          或自行輸入
        </button>
        {error && <p className="mt-2 text-xs text-[var(--color-accent-hover)]">{error}</p>}
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-[var(--color-ai-text)]">職責理解</h2>
          {section.quota_remaining != null && section.quota_remaining >= 0 && (
            <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">
              LinkedIn 更新 本月剩 {section.quota_remaining} 次
            </p>
          )}
        </div>
        {chip && hasContent && (
          <span
            className={cn(
              "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
              chip.className,
            )}
          >
            {chip.label}
          </span>
        )}
      </div>

      {editing ? (
        <form onSubmit={saveInline} className="mt-3">
          <label className="block text-xs text-[var(--color-text-secondary)]">
            可能負責的業務範圍（儲存後標示為使用者筆記）
          </label>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value.slice(0, MAX_LEN))}
            rows={4}
            className="mt-1 w-full resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]"
            autoFocus
            required
          />
          <p className="mt-1 text-right text-[10px] text-[var(--color-text-tertiary)]">
            {draft.length}/{MAX_LEN}
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="flex-1 rounded-lg border border-[var(--color-border)] py-2 text-sm text-[var(--color-text-secondary)]"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!draft.trim() || saveScope.isPending}
              className="flex-1 rounded-lg bg-[var(--color-primary)] py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saveScope.isPending ? "儲存中…" : "儲存"}
            </button>
          </div>
        </form>
      ) : (
        <>
          {hasContent ? (
            <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-primary)]">
              {section.person_scope}
            </p>
          ) : (
            <div className="mt-3">
              <p className="text-sm text-[var(--color-text-secondary)]">
                尚無內容。建議先從 LinkedIn 公開資料更新，準確度通常較高。
              </p>
              {showInsufficientNote && (
                <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">
                  {section.message ||
                    "上次 AI 更新未能達可靠標準，你可再試一次或改為自行輸入。"}
                </p>
              )}
              {!hasLinkedIn && (
                <p className="mt-2 text-xs text-[var(--color-accent-hover)]">
                  尚未填寫 LinkedIn 個人頁網址，請先透過右上角「編輯」補上。
                </p>
              )}
            </div>
          )}

          {isEmpty && (
            <div className="mt-4 space-y-2">
              <button
                type="button"
                disabled={linkedInBusy || section.can_enrich === false}
                onClick={runLinkedInUpdate}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[var(--color-primary)] py-2.5 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
              >
                {linkedInBusy
                  ? "更新中…"
                  : hasLinkedIn
                    ? "✨ 從 LinkedIn 更新"
                    : "先填 LinkedIn 再更新"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={startInlineEdit}
                className="w-full py-1 text-center text-xs text-[var(--color-text-tertiary)] underline-offset-2 hover:text-[var(--color-primary)] hover:underline"
              >
                或自行輸入
              </button>
            </div>
          )}

          {hasContent && (
            <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-[var(--color-ai-border)] pt-3">
              <button
                type="button"
                disabled={busy}
                onClick={startInlineEdit}
                className="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-primary)]"
              >
                編輯
              </button>
              <span className="text-[var(--color-border)]">|</span>
              <button
                type="button"
                disabled={linkedInBusy || section.can_enrich === false}
                onClick={runLinkedInUpdate}
                className="text-xs font-medium text-[var(--color-primary)] disabled:opacity-50"
              >
                {linkedInBusy ? "更新中…" : "從 LinkedIn 更新"}
              </button>
              <span className="text-[var(--color-border)]">|</span>
              <button
                type="button"
                disabled={busy}
                onClick={clearContent}
                className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-error)]"
              >
                清除
              </button>
            </div>
          )}
        </>
      )}

      {error && <p className="mt-2 text-xs text-[var(--color-accent-hover)]">{error}</p>}
    </section>
  );
}

function formatError(err: unknown): string {
  const msg = err instanceof Error ? err.message : "操作失敗";
  if (msg.includes("PERSON_LINKEDIN_QUOTA_EXCEEDED")) return "本月 LinkedIn 更新次數已用完";
  if (msg.includes("PERSON_ENRICH_IN_PROGRESS")) return "正在更新中，請稍候";
  if (msg.includes("PERSON_ENRICH_NOT_ALLOWED")) return "需要 Pro 方案";
  return "無法完成更新，請稍後再試";
}

function formatScopeError(err: unknown): string {
  const msg = err instanceof Error ? err.message : "儲存失敗";
  if (msg.includes("CONTACT_VERSION_CONFLICT")) return "資料已被更新，請重新整理後再試";
  if (msg.includes("PERSON_ENRICH_NOT_ALLOWED")) return "需要 Pro 方案";
  return "無法儲存，請稍後再試";
}
