"use client";

import Link from "next/link";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import { EmptyState } from "@/shared/components/EmptyState";

export function CapturePage() {
  return (
    <main className="flex flex-col gap-6 p-4">
      <EmptyState
        title="開始收錄名片"
        description="連續拍攝名片，OCR 會在背景處理。您只需之後確認姓名、公司、抬頭。"
      />
      <div className="flex flex-col gap-3">
        <Link
          href="/capture/burst"
          className="rounded-xl bg-[var(--color-accent)] px-4 py-4 text-center text-base font-semibold text-white hover:bg-[var(--color-accent-hover)]"
        >
          連拍收錄
        </Link>
        <Link
          href="/review"
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-center text-sm text-[var(--color-text-primary)]"
        >
          查看待確認
        </Link>
      </div>
      <PrivacyStrip />
    </main>
  );
}
