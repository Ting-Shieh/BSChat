"use client";

import Link from "next/link";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import { EmptyState } from "@/shared/components/EmptyState";

export function CapturePage() {
  return (
    <main className="flex flex-col gap-6 p-4">
      <EmptyState
        title="開始收錄名片"
        description="連續拍攝紙本名片，或貼連結 / 掃 QR 收電子名片。背景處理後可搜尋。"
      />
      <div className="flex flex-col gap-3">
        <Link
          href="/capture/burst"
          className="rounded-xl bg-[var(--color-accent)] px-4 py-4 text-center text-base font-semibold text-white hover:bg-[var(--color-accent-hover)]"
        >
          連拍收錄
        </Link>
        <Link
          href="/capture/import-url"
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-center text-sm text-[var(--color-text-primary)]"
        >
          🔗 貼連結收電子名片
        </Link>
        <Link
          href="/capture/scan-qr"
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-center text-sm text-[var(--color-text-primary)]"
        >
          📷 掃 QR 收電子名片
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
