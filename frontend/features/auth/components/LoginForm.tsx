"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { googleStartUrl } from "../api";
import { useAuthMode, usePasswordLogin } from "../hooks";
import { ApiError } from "@/shared/lib/api-client";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const inviteToken = params.get("invite") || undefined;
  const inviteEnterprise = params.get("invite_enterprise") || undefined;
  const { data: mode } = useAuthMode();
  const login = usePasswordLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const showGoogle = Boolean(mode?.google_enabled);

  function afterAuth() {
    if (inviteEnterprise) {
      router.push(`/join/enterprise/${encodeURIComponent(inviteEnterprise)}`);
    } else if (inviteToken) {
      router.push(`/join/${encodeURIComponent(inviteToken)}`);
    } else {
      router.push("/contacts");
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: afterAuth,
        onError: (err) => {
          if (err instanceof ApiError && err.message.includes("INVALID_CREDENTIALS")) {
            setError("Email 或密碼不正確");
          } else {
            setError(err instanceof Error ? err.message : "登入失敗");
          }
        },
      },
    );
  }

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div>
          <label className="mb-1.5 block text-[12.5px] font-medium text-[var(--color-text-primary)]">
            Email
          </label>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
            placeholder="you@company.com"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-[12.5px] font-medium text-[var(--color-text-primary)]">
            密碼
          </label>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            placeholder="••••••••"
          />
          <div className="mt-1.5 text-right">
            <Link
              href="/forgot-password"
              className="text-[13px] font-medium text-[var(--color-primary)]"
            >
              忘記密碼？
            </Link>
          </div>
        </div>
        {error && <p className="text-[12.5px] text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={login.isPending}
          className="h-11 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
        >
          {login.isPending ? "登入中…" : "登入"}
        </button>
      </form>

      {showGoogle && (
        <>
          <div className="relative text-center text-[11px] text-[var(--color-text-tertiary)]">
            <span className="relative z-10 bg-[var(--color-bg)] px-2">或</span>
            <div className="absolute inset-x-0 top-1/2 border-t border-[var(--color-border)]" />
          </div>
          <button
            type="button"
            onClick={() => {
              window.location.href = googleStartUrl(inviteToken);
            }}
            className="h-11 rounded-lg border border-[var(--color-border)] bg-white text-sm font-semibold text-[var(--color-text-primary)]"
          >
            使用 Google 繼續
          </button>
        </>
      )}

      <p className="text-center text-[13px] text-[var(--color-text-secondary)]">
        沒有帳號？{" "}
        <Link
          href={
            inviteEnterprise
              ? `/register?invite_enterprise=${encodeURIComponent(inviteEnterprise)}`
              : inviteToken
                ? `/register?invite=${encodeURIComponent(inviteToken)}`
                : "/register"
          }
          className="font-medium text-[var(--color-primary)]"
        >
          註冊
        </Link>
      </p>
    </div>
  );
}
