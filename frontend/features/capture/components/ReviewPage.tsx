"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import { EmptyState } from "@/shared/components/EmptyState";
import { useAuthStore } from "@/features/auth/store";
import type { CardListItem } from "@/shared/types/capture";
import * as captureApi from "../api";
import { useCards } from "../hooks";
import { ActionToast } from "./ActionToast";
import { DeleteCardDialog } from "./DeleteCardDialog";

function field(fields: Record<string, unknown> | undefined, key: string) {
  const v = fields?.[key];
  return typeof v === "string" ? v : "—";
}

function EngineBadge({ engine }: { engine?: string | null }) {
  const isMock = engine === "mock-ocr" || !engine;
  return (
    <span
      className={
        isMock
          ? "rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700"
          : "rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800"
      }
    >
      {isMock ? "假資料" : engine === "import" ? "匯入" : "Gemini"}
    </span>
  );
}

function CardFields({ card }: { card: CardListItem }) {
  const fields = card.ocr_summary?.extracted_fields ?? {};
  const conf = card.ocr_summary?.field_confidences ?? {};
  const engine = card.ocr_summary?.engine;

  return (
    <div className="min-w-0 flex-1">
      <div className="mb-1 flex items-center gap-2">
        <EngineBadge engine={engine} />
      </div>
      <p className="flex items-center gap-2 font-medium text-[var(--color-text-primary)]">
        <ConfidenceDot confidence={conf.name} />
        {field(fields, "name")}
      </p>
      <p className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
        <ConfidenceDot confidence={conf.company} />
        {field(fields, "company")}
      </p>
      <p className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
        <ConfidenceDot confidence={conf.title} />
        {field(fields, "title")}
      </p>
    </div>
  );
}

type ReviewCardRowProps = {
  card: CardListItem;
  onSkip?: () => void;
  onDelete: () => void;
  onReocr?: () => void;
  reocrPending?: boolean;
  skipPending?: boolean;
};

function ReviewCardRow({ card, onSkip, onDelete, onReocr, reocrPending, skipPending }: ReviewCardRowProps) {
  const engine = card.ocr_summary?.engine;
  const isMock = engine === "mock-ocr" || !engine;

  return (
    <div className="flex gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <Link href={`/review/${card.id}`} className="flex min-w-0 flex-1 gap-3">
        {card.image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={card.image_url} alt="" className="h-20 w-14 shrink-0 rounded object-cover" />
        )}
        <CardFields card={card} />
      </Link>
      <div className="flex shrink-0 flex-col items-end justify-center gap-1">
        {onSkip && (
          <button
            type="button"
            disabled={skipPending}
            onClick={onSkip}
            className="rounded-lg border border-[var(--color-border)] px-2 py-1 text-xs text-[var(--color-text-secondary)]"
          >
            稍後
          </button>
        )}
        {isMock && onReocr && (
          <button
            type="button"
            disabled={reocrPending}
            onClick={onReocr}
            className="rounded-lg border border-[var(--color-accent)] px-2 py-1 text-xs text-[var(--color-accent-hover)]"
          >
            重新 OCR
          </button>
        )}
        <button
          type="button"
          onClick={onDelete}
          className="px-2 py-1 text-xs text-[var(--color-error)]"
        >
          刪除
        </button>
      </div>
    </div>
  );
}

export function ReviewPage() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data, isLoading } = useCards({ review_status: "pending_review", status: "ocr_done" });
  const [toast, setToast] = useState<string | null>(null);
  const [deferredOpen, setDeferredOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CardListItem | null>(null);

  const allPending = data?.items ?? [];
  const activePending = allPending.filter((c) => !c.review_deferred_at);
  const deferredPending = allPending.filter((c) => c.review_deferred_at);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["cards"] });
    queryClient.invalidateQueries({ queryKey: ["pending-count"] });
    queryClient.invalidateQueries({ queryKey: ["contacts"] });
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  };

  const skip = useMutation({
    mutationFn: (cardId: string) => captureApi.skipReviewCard(token!, cardId),
    onSuccess: () => {
      invalidate();
      showToast("已跳過，仍可在搜尋中找到這位聯絡人");
    },
  });

  const remove = useMutation({
    mutationFn: (cardId: string) => captureApi.deleteCard(token!, cardId),
    onSuccess: () => {
      invalidate();
      setDeleteTarget(null);
      showToast("已刪除");
    },
  });

  const reocr = useMutation({
    mutationFn: (cardId: string) => captureApi.reocrCard(token!, cardId),
    onSuccess: () => invalidate(),
  });

  const openDelete = (card: CardListItem) => setDeleteTarget(card);

  if (isLoading) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  const hasAny = activePending.length > 0 || deferredPending.length > 0;

  return (
    <main className="flex flex-col gap-4 p-4">
      {activePending.length > 0 && (
        <section className="flex flex-col gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              需核對 · {activePending.length}
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)]">請確認姓名、公司、抬頭三欄</p>
          </div>
          {activePending.map((card) => (
            <ReviewCardRow
              key={card.id}
              card={card}
              onSkip={() => skip.mutate(card.id)}
              onDelete={() => openDelete(card)}
              onReocr={() => reocr.mutate(card.id)}
              reocrPending={reocr.isPending}
              skipPending={skip.isPending}
            />
          ))}
        </section>
      )}

      {deferredPending.length > 0 && (
        <section className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => setDeferredOpen((v) => !v)}
            className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-primary-muted)] px-3 py-2 text-left text-sm text-[var(--color-text-secondary)]"
          >
            <span>稍後再核對 · {deferredPending.length}</span>
            <span aria-hidden>{deferredOpen ? "▾" : "▸"}</span>
          </button>
          {deferredOpen &&
            deferredPending.map((card) => (
              <ReviewCardRow
                key={card.id}
                card={card}
                onDelete={() => openDelete(card)}
                onReocr={() => reocr.mutate(card.id)}
                reocrPending={reocr.isPending}
              />
            ))}
        </section>
      )}

      {!hasAny && (
        <EmptyState
          title="沒有待確認名片"
          description="低信心度結果會出現在這裡。高信心度或已確認的名片請至名片庫查看。"
        />
      )}

      <DeleteCardDialog
        open={!!deleteTarget}
        name={field(deleteTarget?.ocr_summary?.extracted_fields, "name")}
        company={field(deleteTarget?.ocr_summary?.extracted_fields, "company")}
        pending={remove.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
      />
      <ActionToast message={toast} />
    </main>
  );
}
