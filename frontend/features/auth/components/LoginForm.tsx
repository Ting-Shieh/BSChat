"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import type { PlanTier } from "@/shared/types/auth";
import { cn } from "@/shared/lib/cn";
import { useDevLogin } from "../hooks";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]";

const PLAN_OPTIONS: { id: PlanTier; label: string; hint: string }[] = [
  { id: "free", label: "Free", hint: "M3 推估 · 公司補全 · 有限額度" },
  { id: "pro", label: "Pro", hint: "含 LinkedIn 補充 · 較高配額" },
  { id: "enterprise", label: "企業版", hint: "管理公開商務目錄 · 含 demo 種子" },
];

/** 各方案預設 dev 帳號（分開 email 才有獨立聯絡人與額度） */
const DEV_ACCOUNT_BY_PLAN: Record<PlanTier, { email: string; displayName: string }> = {
  free: { email: "dev-free@example.com", displayName: "Dev (Free)" },
  pro: { email: "dev-pro@example.com", displayName: "Dev (Pro)" },
  enterprise: { email: "dev-enterprise@example.com", displayName: "Dev (Enterprise)" },
};

export function LoginForm() {
  const router = useRouter();
  const login = useDevLogin();
  const [planTier, setPlanTier] = useState<PlanTier>("free");
  const [email, setEmail] = useState(DEV_ACCOUNT_BY_PLAN.free.email);
  const [displayName, setDisplayName] = useState(DEV_ACCOUNT_BY_PLAN.free.displayName);
  const [companyCode, setCompanyCode] = useState("");

  function selectPlan(tier: PlanTier) {
    setPlanTier(tier);
    const preset = DEV_ACCOUNT_BY_PLAN[tier];
    setEmail(preset.email);
    setDisplayName(preset.displayName);
    if (tier === "enterprise" && !companyCode.trim()) {
      setCompanyCode("acme-demo");
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const org =
      companyCode.trim().toLowerCase() ||
      (planTier === "enterprise" ? "acme-demo" : undefined);
    login.mutate(
      {
        email,
        display_name: displayName,
        plan_tier: planTier,
        seed_org: org || undefined,
      },
      {
        onSuccess: () =>
          router.push(planTier === "enterprise" && org === "acme-demo" ? "/admin/org" : "/contacts"),
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <p className="mb-2 text-sm font-medium text-[var(--color-text-primary)]">方案（開發用）</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {PLAN_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => selectPlan(opt.id)}
              className={cn(
                "rounded-lg border px-3 py-2 text-left transition-colors",
                planTier === opt.id
                  ? "border-[var(--color-primary)] bg-[var(--color-ai-bg)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-text-tertiary)]",
              )}
            >
              <span
                className={cn(
                  "block text-sm font-medium",
                  planTier === opt.id
                    ? "text-[var(--color-primary)]"
                    : "text-[var(--color-text-secondary)]",
                )}
              >
                {opt.label}
              </span>
              <span className="mt-0.5 block text-[10px] leading-tight text-[var(--color-text-tertiary)]">
                {opt.hint}
              </span>
            </button>
          ))}
        </div>
      </div>
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
      <div>
        <label htmlFor="org" className="mb-1 block text-sm text-[var(--color-text-secondary)]">
          公司代號（團隊共享）
        </label>
        <input
          id="org"
          type="text"
          value={companyCode}
          onChange={(e) => setCompanyCode(e.target.value)}
          placeholder="例：acme-demo（同代號＝同一團隊池）"
          className={inputClass}
          autoComplete="organization"
        />
        <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
          填了才進團隊共享池；留空則只有自己看得到。
        </p>
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
