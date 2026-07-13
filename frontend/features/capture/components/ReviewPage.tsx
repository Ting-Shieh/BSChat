"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState } from "@/shared/components/EmptyState";
import { resolveMediaUrl } from "@/shared/lib/media-url";
import { useAuthStore } from "@/features/auth/store";
import type { CardListItem } from "@/shared/types/capture";
import * as captureApi from "../api";
import { useCards } from "../hooks";
import { ActionToast } from "./ActionToast";

function field(fields: Record<string, unknown> | undefined, key: string) {
  const v = fields?.[key];
  return typeof v === "string" ? v : "—";
}

function confOf(conf: Record<string, number> | undefined, key: string) {
  const v = conf?.[key];
  return typeof v === "number" ? v : 1;
}

/** Low confidence → amber “建議確認”; otherwise green. */
function ConfidenceMark({ confidence }: { confidence: number }) {
  const low = confidence < 0.75;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={
          low
            ? "inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-warning)]"
            : "inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-success)]"
        }
      />
      {low && (
        <span className="text-[11px] font-normal text-[var(--color-warning)]">建議確認</span>
      )}
    </span>
  );
}

export function ReviewPage() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data, isLoading } = useCards({ review_status: "pending_review", status: "ocr_done" });
  const [toast, setToast] = useState<string | null>(null);
  const [index, setIndex] = useState(0);

  const allPending = data?.items ?? [];
  const activePending = allPending.filter((c) => !c.review_deferred_at);
  const deferredCount = allPending.filter((c) => c.review_deferred_at).length;
  const card: CardListItem | undefined = activePending[Math.min(index, Math.max(activePending.length - 1, 0))];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["cards"] });
    queryClient.invalidateQueries({ queryKey: ["pending-count"] });
    queryClient.invalidateQueries({ queryKey: ["contacts"] });
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  };

  const confirm = useMutation({
    mutationFn: async (c: CardListItem) => {
      let version = c.version;
      let fields = c.ocr_summary?.extracted_fields ?? {};
      if (version == null) {
        const detail = await captureApi.getCard(token!, c.id);
        version = detail.version;
        fields = detail.ocr_result?.extracted_fields ?? fields;
      }
      return captureApi.reviewCard(token!, c.id, {
        name: typeof fields.name === "string" ? fields.name : undefined,
        company: typeof fields.company === "string" ? fields.company : undefined,
        title: typeof fields.title === "string" ? fields.title : undefined,
        version,
      });
    },
    onSuccess: () => {
      invalidate();
      showToast("已確認 ✓");
      setIndex(0);
    },
  });

  const skip = useMutation({
    mutationFn: (cardId: string) => captureApi.skipReviewCard(token!, cardId),
    onSuccess: () => {
      invalidate();
      showToast("已跳過，仍可在搜尋中找到這位聯絡人");
      setIndex(0);
    },
  });

  if (isLoading) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  if (!card) {
    return (
      <main className="flex flex-col gap-4 p-4">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">待確認</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            只要確認姓名／公司對不對，其他 AI 都處理好了
          </p>
        </div>
        <EmptyState
          title="沒有待確認名片"
          description="低信心結果會出現在這裡。高信心或已確認的請至名片庫查看。不阻擋搜尋。"
        />
        {deferredCount > 0 && (
          <p className="text-center text-xs text-[var(--color-text-tertiary)]">
            稍後再核對 · {deferredCount} 張（仍可搜尋）
          </p>
        )}
        <Link href="/contacts" className="text-center text-sm text-[var(--color-primary)]">
          去名片庫 →
        </Link>
        <ActionToast message={toast} />
      </main>
    );
  }

  const fields = card.ocr_summary?.extracted_fields ?? {};
  const conf = card.ocr_summary?.field_confidences ?? {};
  const name = field(fields, "name");
  const company = field(fields, "company");
  const title = field(fields, "title");
  const phone = field(fields, "phone");
  const imageSrc = resolveMediaUrl(card.image_url);
  const busy = confirm.isPending || skip.isPending;
  const remaining = activePending.length;

  return (
    <main className="flex min-h-[70vh] flex-col p-4">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
          待確認{" "}
          <span className="text-[13px] font-medium text-[var(--color-warning)]">· 還有 {remaining} 張</span>
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          只要確認<b className="font-semibold text-[var(--color-text-primary)]">姓名 / 公司</b>
          對不對，其他 AI 都處理好了
        </p>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center py-6">
        <div className="w-full max-w-sm overflow-hidden rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[0_8px_24px_rgba(28,25,23,0.1)]">
          <div className="flex h-[120px] items-center justify-center bg-[#292524]">
            {imageSrc ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={imageSrc}
                alt=""
                className="h-[88px] w-[210px] -rotate-2 rounded-md bg-white object-cover shadow-md"
              />
            ) : (
              <div className="flex h-[88px] w-[210px] -rotate-2 flex-col justify-center rounded-md bg-white px-3 py-2 shadow-md">
                <p className="text-[13px] font-bold text-[var(--color-text-primary)]">{name}</p>
                <p className="text-[9px] text-[var(--color-text-secondary)]">
                  {company}
                  {title !== "—" ? ` · ${title}` : ""}
                </p>
                {phone !== "—" && (
                  <p className="mt-2 font-mono text-[8px] text-[var(--color-text-tertiary)]">{phone}</p>
                )}
              </div>
            )}
          </div>

          <div className="px-4 py-3.5">
            <p className="text-[11px] text-[var(--color-text-tertiary)]">姓名</p>
            <p className="mt-1 flex items-center gap-2 text-base font-semibold text-[var(--color-text-primary)]">
              {name}
              <ConfidenceMark confidence={confOf(conf, "name")} />
            </p>
            <p className="mt-3 text-[11px] text-[var(--color-text-tertiary)]">公司</p>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-base font-semibold text-[var(--color-text-primary)]">
              {company}
              <ConfidenceMark confidence={confOf(conf, "company")} />
            </p>
          </div>

          <div className="flex border-t border-[var(--color-border)]">
            <button
              type="button"
              disabled={busy}
              onClick={() => skip.mutate(card.id)}
              className="flex-1 py-3.5 text-sm text-[var(--color-text-secondary)] disabled:opacity-50"
            >
              ← 跳過
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => confirm.mutate(card)}
              className="flex-1 border-l border-[var(--color-border)] py-3.5 text-sm font-semibold text-[var(--color-success)] disabled:opacity-50"
            >
              {confirm.isPending ? "確認中…" : "確認 →"}
            </button>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-[var(--color-text-tertiary)]">
          確認＝姓名／公司沒問題 · 跳過＝稍後再說 ·{" "}
          <Link href={`/review/${card.id}`} className="text-[var(--color-text-secondary)] underline">
            改欄位
          </Link>
        </p>
        {deferredCount > 0 && (
          <p className="mt-2 text-center text-[11px] text-[var(--color-text-tertiary)]">
            稍後再核對 · {deferredCount} 張（仍可搜尋）
          </p>
        )}
      </div>

      <ActionToast message={toast} />
    </main>
  );
}
