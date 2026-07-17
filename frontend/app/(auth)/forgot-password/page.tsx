"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useForgotPassword } from "@/features/auth/hooks";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-primary)]";

export default function ForgotPasswordPage() {
  const forgot = useForgotPassword();
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    forgot.mutate(email.trim(), {
      onSuccess: () => setDone(true),
      onError: (err) => setError(err instanceof Error ? err.message : "寄送失敗"),
    });
  }

  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">重設密碼</p>
      </div>
      <div className="w-full max-w-sm">
        {done ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-800">
            若此 Email 已註冊，重設信件將寄出。請至信箱開啟連結。
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                placeholder="you@company.com"
              />
            </div>
            {error && <p className="text-[12.5px] text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={forgot.isPending}
              className="h-11 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
            >
              {forgot.isPending ? "寄送中…" : "寄送重設連結"}
            </button>
          </form>
        )}
        <p className="mt-6 text-center text-[13px] text-[var(--color-text-secondary)]">
          <Link href="/login" className="font-medium text-[var(--color-primary)]">
            ← 回到登入
          </Link>
        </p>
      </div>
      <PrivacyStrip />
    </main>
  );
}
