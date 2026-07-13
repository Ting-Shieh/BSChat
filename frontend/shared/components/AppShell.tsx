"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useMe } from "@/features/auth/hooks";
import { useAuthHydrated } from "@/features/auth/useAuthHydrated";
import { usePendingCount } from "@/features/capture/hooks";
import { useAuthStore } from "@/features/auth/store";
import { cn } from "@/shared/lib/cn";

const tabs = [
  { href: "/search", label: "搜尋", icon: "🔍" },
  { href: "/contacts", label: "名片庫", icon: "📇" },
  { href: "/capture", label: "收錄", icon: "＋", elevate: true as const },
  { href: "/review", label: "待確認", icon: "✓", badge: true as const },
  { href: "/settings", label: "我的", icon: "👤" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const hydrated = useAuthHydrated();
  const token = useAuthStore((s) => s.token);
  const { data: me, isError: meError } = useMe();
  const { data: pending } = usePendingCount();
  const logout = useAuthStore((s) => s.logout);

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

  const isEnterprise = me?.plan_tier === "enterprise";
  const hideChrome =
    pathname.startsWith("/capture/burst") ||
    pathname.startsWith("/capture/scan-qr");

  return (
    <div className="flex min-h-full flex-1 flex-col">
      {!hideChrome && (
        <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
          <div>
            <p className="text-sm font-medium text-[var(--color-text-primary)]">
              {me?.display_name ?? "BSChat"}
            </p>
            <p className="text-xs text-[var(--color-text-tertiary)]">
              {me?.plan_tier ?? "free"} plan
            </p>
          </div>
          {isEnterprise && (
            <Link
              href="/admin/org"
              className={cn(
                "text-xs",
                pathname.startsWith("/admin/org")
                  ? "font-semibold text-[var(--color-primary)]"
                  : "text-[var(--color-text-secondary)]",
              )}
            >
              公開目錄
            </Link>
          )}
        </header>
      )}

      <div className="flex-1">{children}</div>

      {!hideChrome && (
        <nav className="sticky bottom-0 border-t border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur">
          <ul className="flex items-end px-1">
            {tabs.map((tab) => {
              const active = pathname.startsWith(tab.href);
              if (tab.elevate) {
                return (
                  <li key={tab.href} className="relative flex-1">
                    <Link
                      href={tab.href}
                      className="flex flex-col items-center gap-0.5 pb-2 pt-1 text-[10px] text-[var(--color-text-secondary)]"
                    >
                      <span className="-mt-3 flex h-[38px] w-[38px] items-center justify-center rounded-full bg-[var(--color-accent)] text-xl font-bold text-white shadow-[0_4px_10px_rgba(217,119,6,0.35)]">
                        {tab.icon}
                      </span>
                      <span className={cn(active && "font-semibold text-[var(--color-primary)]")}>
                        {tab.label}
                      </span>
                    </Link>
                  </li>
                );
              }
              return (
                <li key={tab.href} className="relative flex-1">
                  <Link
                    href={tab.href}
                    className={cn(
                      "flex flex-col items-center gap-0.5 py-2.5 text-[10px]",
                      active
                        ? "font-semibold text-[var(--color-primary)]"
                        : "text-[var(--color-text-secondary)]",
                    )}
                  >
                    <span className="relative text-base leading-none">
                      {tab.icon}
                      {tab.badge && (pending?.count ?? 0) > 0 && (
                        <span className="absolute -right-2.5 -top-1.5 inline-flex h-[15px] min-w-[15px] items-center justify-center rounded-full bg-[var(--color-warning)] px-0.5 text-[9px] font-semibold text-white">
                          {pending!.count > 9 ? "9+" : pending!.count}
                        </span>
                      )}
                    </span>
                    <span>{tab.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      )}
    </div>
  );
}
