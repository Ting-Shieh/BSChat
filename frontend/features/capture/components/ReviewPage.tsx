"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import { EmptyState } from "@/shared/components/EmptyState";
import { useAuthStore } from "@/features/auth/store";
import * as captureApi from "../api";
import { useCards } from "../hooks";

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
      {isMock ? "假資料" : "Gemini"}
    </span>
  );
}

export function ReviewPage() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data, isLoading } = useCards({ review_status: "pending_review", status: "ocr_done" });
  const { data: recent } = useCards({ status: "ocr_done" });
  const items = data?.items ?? [];
  const autoAccepted = (recent?.items ?? []).filter((c) => c.review_status === "auto_accepted").slice(0, 3);

  const reocr = useMutation({
    mutationFn: (cardId: string) => captureApi.reocrCard(token!, cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cards"] });
      queryClient.invalidateQueries({ queryKey: ["pending-count"] });
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });

  if (isLoading) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  return (
    <main className="flex flex-col gap-4 p-4">
      {autoAccepted.length > 0 && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
          <p className="mb-2 text-sm font-medium text-emerald-800">已自動確認（Gemini 高信心度）</p>
          <ul className="space-y-1 text-sm text-[var(--color-text-primary)]">
            {autoAccepted.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-2">
                <span>
                  {field(c.ocr_summary?.extracted_fields, "name")} ·{" "}
                  {field(c.ocr_summary?.extracted_fields, "company")}
                </span>
                <EngineBadge engine={c.ocr_summary?.engine} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="沒有待確認名片"
          description="低信心度結果會出現在這裡。高信心度會自動確認（見上方）。"
        />
      ) : (
        <>
          <p className="text-sm text-[var(--color-text-secondary)]">僅需確認姓名、公司、抬頭三欄</p>
          {items.map((card) => {
            const fields = card.ocr_summary?.extracted_fields ?? {};
            const conf = card.ocr_summary?.field_confidences ?? {};
            const engine = card.ocr_summary?.engine;
            const isMock = engine === "mock-ocr" || !engine;

            return (
              <div
                key={card.id}
                className="flex gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3"
              >
                <Link href={`/review/${card.id}`} className="flex min-w-0 flex-1 gap-3">
                  {card.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={card.image_url} alt="" className="h-20 w-14 shrink-0 rounded object-cover" />
                  )}
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
                </Link>
                {isMock && (
                  <button
                    type="button"
                    disabled={reocr.isPending}
                    onClick={() => reocr.mutate(card.id)}
                    className="shrink-0 self-center rounded-lg border border-[var(--color-accent)] px-2 py-1 text-xs text-[var(--color-accent-hover)]"
                  >
                    重新 OCR
                  </button>
                )}
              </div>
            );
          })}
        </>
      )}
    </main>
  );
}
