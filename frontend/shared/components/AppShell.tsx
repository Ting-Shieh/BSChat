"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLogout, useMe, useSwitchPlan } from "@/features/auth/hooks";
import type { PlanTier } from "@/shared/types/auth";
import { useAuthHydrated } from "@/features/auth/useAuthHydrated";
import { usePendingCount } from "@/features/capture/hooks";
import { useAuthStore } from "@/features/auth/store";
import { cn } from "@/shared/lib/cn";

const tabs = [
  { href: "/search", label: "搜尋" },
  { href: "/contacts", label: "聯絡人" },
  { href: "/capture", label: "收錄" },
  { href: "/review", label: "待確認", badge: true as const },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const hydrated = useAuthHydrated();
  const token = useAuthStore((s) => s.token);
  const logout = useLogout();
  const { data: me, isError: meError } = useMe();
  const switchPlan = useSwitchPlan();
  const { data: pending } = usePendingCount();
  const isPro = me?.plan_tier === "pro" || me?.plan_tier === "enterprise";

  useEffect(() => {
    if (hydrated && !token) router.replace("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (meError) {
      logout();
      router.replace("/login");
    }
  }, [meError, logout, router]);

  if (!hydrated) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">
        導向登入…
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">
            {me?.display_name ?? "BSChat"}
          </p>
          <p className="text-xs text-[var(--color-text-tertiary)]">
            {me?.plan_tier ?? "free"} plan
            {me?.quotas?.person_linkedin_remaining_month != null && isPro && (
              <> · LinkedIn 剩 {me.quotas.person_linkedin_remaining_month}</>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={switchPlan.isPending}
            onClick={() => switchPlan.mutate((isPro ? "free" : "pro") as PlanTier)}
            className="rounded border border-[var(--color-border)] px-2 py-1 text-[10px] text-[var(--color-primary)] disabled:opacity-50"
          >
            {isPro ? "改 Free" : "試用 Pro"}
          </button>
          <button
            type="button"
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-primary)]"
          >
            登出
          </button>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <nav className="sticky bottom-0 border-t border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur">
        <ul className="flex">
          {tabs.map((tab) => (
            <li key={tab.href} className="relative flex-1">
              <Link
                href={tab.href}
                className={cn(
                  "block py-3 text-center text-sm",
                  pathname.startsWith(tab.href)
                    ? "font-semibold text-[var(--color-primary)]"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
                )}
              >
                {tab.label}
                {tab.badge && (pending?.count ?? 0) > 0 && (
                  <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-accent)] px-1 text-[10px] text-white">
                    {pending!.count}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
