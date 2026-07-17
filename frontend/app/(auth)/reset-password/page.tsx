"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { useResetPassword } from "@/features/auth/hooks";
import { ApiError } from "@/shared/lib/api-client";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-primary)]";

function ResetBody() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const reset = useResetPassword();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return (
      <div className="w-full max-w-sm text-center text-sm text-red-600">
        連結無效。請重新申請重設密碼。
        <p className="mt-4">
          <Link href="/forgot-password" className="text-[var(--color-primary)]">
            忘記密碼
          </Link>
        </p>
      </div>
    );
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("密碼至少 8 個字元");
      return;
    }
    if (password !== confirm) {
      setError("兩次密碼不一致");
      return;
    }
    reset.mutate(
      { token, new_password: password },
      {
        onSuccess: () => router.push("/contacts"),
        onError: (err) => {
          if (err instanceof ApiError && err.message.includes("RESET_TOKEN_INVALID")) {
            setError("連結已失效，請重新申請");
          } else {
            setError(err instanceof Error ? err.message : "重設失敗");
          }
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-3">
      <div>
        <label className="mb-1.5 block text-[12.5px] font-medium">新密碼</label>
        <input
          type="password"
          required
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass}
          placeholder="至少 8 個字元"
        />
      </div>
      <div>
        <label className="mb-1.5 block text-[12.5px] font-medium">確認新密碼</label>
        <input
          type="password"
          required
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className={inputClass}
        />
      </div>
      {error && <p className="text-[12.5px] text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={reset.isPending}
        className="h-11 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
      >
        {reset.isPending ? "儲存中…" : "儲存並登入"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">設定新密碼</p>
      </div>
      <Suspense fallback={<p className="text-sm">載入中…</p>}>
        <ResetBody />
      </Suspense>
      <PrivacyStrip />
    </main>
  );
}
