"use client";

import Link from "next/link";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

export function CapturePage() {
  return (
    <main className="flex flex-col gap-5 p-4">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">收錄</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          對準名片連續拍 —— <span className="font-medium text-[var(--color-text-primary)]">不用填任何欄位</span>
        </p>
      </div>

      {/* Hero — 連拍主動作（對齊 screen-flow） */}
      <Link
        href="/capture/burst"
        className="relative block overflow-hidden rounded-2xl bg-[#1C1917] px-5 pb-6 pt-8 text-center shadow-lg"
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,#3f3f46,#1C1917_70%)]" />
        <div className="relative mx-auto mb-5 flex h-[120px] w-[200px] -rotate-2 flex-col justify-center rounded-lg bg-white px-4 py-3 shadow-xl">
          <p className="text-left text-sm font-bold text-[#1C1917]">對準名片</p>
          <p className="mt-1 text-left text-[11px] text-[#57534E]">連續拍 · 零必填</p>
          <p className="mt-3 text-left font-mono text-[9px] text-[#78716C]">AI 背景辨識中…</p>
        </div>
        <p className="relative text-sm text-[#D6D3D1]">
          收名片像拍照，不像填表
        </p>
        <div className="relative mx-auto mt-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-accent)] ring-4 ring-white">
          <span className="text-2xl font-bold text-white">＋</span>
        </div>
        <p className="relative mt-3 text-sm font-semibold text-white">連拍收錄</p>
      </Link>

      <div className="flex flex-col gap-2">
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
