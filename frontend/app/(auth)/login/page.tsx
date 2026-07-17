"use client";

import { Suspense } from "react";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

export default function LoginPage() {
  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          登入以繼續使用名片庫與 AI 搜尋
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-[var(--color-text-secondary)]">載入中…</p>}>
        <LoginForm />
      </Suspense>
      <PrivacyStrip />
    </main>
  );
}
