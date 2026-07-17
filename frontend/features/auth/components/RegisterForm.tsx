"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { googleStartUrl } from "../api";
import { useAuthMode, useRegister } from "../hooks";
import { ApiError } from "@/shared/lib/api-client";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]";

export function RegisterForm() {
  const router = useRouter();
  const params = useSearchParams();
  const inviteToken = params.get("invite") || undefined;
  const inviteEnterprise = params.get("invite_enterprise") || undefined;
  const { data: mode } = useAuthMode();
  const register = useRegister();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
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
    if (password.length < 8) {
      setError("密碼至少 8 個字元");
      return;
    }
    if (password !== confirm) {
      setError("兩次密碼不一致");
      return;
    }
    register.mutate(
      {
        email: email.trim(),
        password,
        display_name: displayName.trim() || undefined,
        // Team invite only; enterprise accept happens on /join/enterprise
        invite_token: inviteEnterprise ? undefined : inviteToken,
      },
      {
        onSuccess: afterAuth,
        onError: (err) => {
          if (err instanceof ApiError && err.message.includes("EMAIL_ALREADY_REGISTERED")) {
            setError("此 Email 已註冊，請登入");
          } else {
            setError(err instanceof Error ? err.message : "註冊失敗");
          }
        },
      },
    );
  }

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div>
          <label className="mb-1.5 block text-[12.5px] font-medium">顯示名稱（選填）</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className={inputClass}
            placeholder="于先生"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-[12.5px] font-medium">Email</label>
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
          <label className="mb-1.5 block text-[12.5px] font-medium">密碼</label>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            placeholder="至少 8 個字元"
          />
          <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">至少 8 個字元</p>
        </div>
        <div>
          <label className="mb-1.5 block text-[12.5px] font-medium">確認密碼</label>
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
          disabled={register.isPending}
          className="h-11 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
        >
          {register.isPending ? "建立中…" : "建立帳號"}
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
            className="h-11 rounded-lg border border-[var(--color-border)] bg-white text-sm font-semibold"
          >
            使用 Google 繼續
          </button>
        </>
      )}

      <p className="text-center text-[13px] text-[var(--color-text-secondary)]">
        已有帳號？{" "}
        <Link
          href={
            inviteEnterprise
              ? `/login?invite_enterprise=${encodeURIComponent(inviteEnterprise)}`
              : inviteToken
                ? `/login?invite=${encodeURIComponent(inviteToken)}`
                : "/login"
          }
          className="font-medium text-[var(--color-primary)]"
        >
          登入
        </Link>
      </p>
      <p className="text-center text-[11px] leading-relaxed text-[var(--color-text-tertiary)]">
        註冊即建立 Free 帳號，含公開推薦終身試用 2 次。
      </p>
    </div>
  );
}
