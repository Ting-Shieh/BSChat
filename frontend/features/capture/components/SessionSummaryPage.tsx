"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCaptureSession, useCards } from "../hooks";

export function SessionSummaryPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const { data: session } = useCaptureSession(sessionId);
  const { data: cards } = useCards({ session_id: sessionId });

  const items = cards?.items ?? [];
  const ocrDone = items.filter((c) => c.status === "ocr_done").length;
  const failed = items.filter((c) => ["ocr_failed", "upload_failed"].includes(c.status)).length;
  const processing = items.length - ocrDone - failed;
  const showAha = ocrDone >= 3;

  return (
    <main className="flex flex-col gap-6 p-4">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">收錄完成</h1>
        {session?.source_label && (
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{session.source_label}</p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-2xl font-semibold text-[var(--color-success)]">{ocrDone}</p>
          <p className="text-xs text-[var(--color-text-tertiary)]">OCR 完成</p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-2xl font-semibold text-[var(--color-warning)]">{processing}</p>
          <p className="text-xs text-[var(--color-text-tertiary)]">處理中</p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-2xl font-semibold text-[var(--color-error)]">{failed}</p>
          <p className="text-xs text-[var(--color-text-tertiary)]">失敗</p>
        </div>
      </div>

      {showAha && (
        <div className="rounded-xl border border-[var(--color-accent-muted)] bg-[var(--color-accent-muted)] p-4">
          <p className="font-medium text-[var(--color-accent-hover)]">🎉 已收錄 {ocrDone} 張名片！</p>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            聯絡人正在建立索引，你可以先核對待確認，或直接試試 AI 搜尋。
          </p>
          <Link
            href="/search"
            className="mt-3 block rounded-xl bg-[var(--color-primary)] py-2.5 text-center text-sm font-medium text-white"
          >
            試試 AI 搜尋 →
          </Link>
        </div>
      )}

      <Link
        href="/review"
        className="rounded-xl bg-[var(--color-primary)] py-3 text-center font-medium text-white"
      >
        前往待確認
      </Link>
      <Link href="/capture" className="text-center text-sm text-[var(--color-text-secondary)]">
        繼續收錄
      </Link>
    </main>
  );
}
