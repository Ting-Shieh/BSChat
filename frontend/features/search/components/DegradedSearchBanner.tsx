"use client";

import Link from "next/link";

export function DegradedSearchBanner() {
  return (
    <div
      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="status"
    >
      AI 排序暫時不可用，已改以簡化方式比對。結果可能較寬鬆；可在{" "}
      <Link href="/settings" className="font-medium underline underline-offset-2">
        設定
      </Link>{" "}
      調整 AI 嚴格度。
    </div>
  );
}
