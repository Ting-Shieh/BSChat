"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useDevLogin } from "../hooks";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]";

export function LoginForm() {
  const router = useRouter();
  const login = useDevLogin();
  const [email, setEmail] = useState("dev@example.com");
  const [displayName, setDisplayName] = useState("Dev User");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    login.mutate(
      { email, display_name: displayName },
      { onSuccess: () => router.push("/contacts") },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <label htmlFor="email" className="mb-1 block text-sm text-[var(--color-text-secondary)]">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClass}
          required
        />
      </div>
      <div>
        <label htmlFor="name" className="mb-1 block text-sm text-[var(--color-text-secondary)]">
          顯示名稱
        </label>
        <input
          id="name"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className={inputClass}
        />
      </div>
      {login.error && (
        <p className="text-sm text-[var(--color-error)]">登入失敗，請確認後端已啟動。</p>
      )}
      <button
        type="submit"
        disabled={login.isPending}
        className="rounded-lg bg-[var(--color-primary)] px-4 py-2.5 font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
      >
        {login.isPending ? "登入中…" : "Dev 登入"}
      </button>
    </form>
  );
}
