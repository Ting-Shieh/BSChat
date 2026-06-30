"use client";

import { useState } from "react";
import { useMe, useSwitchPlan, useUpdateSettings } from "@/features/auth/hooks";
import type { SettingsPayload } from "@/features/auth/hooks";
import { cn } from "@/shared/lib/cn";

const INTERVALS = [30, 60, 90] as const;

const PRECISION_OPTIONS = [
  { id: "strict" as const, label: "精準", desc: "只顯示高度符合的結果" },
  { id: "balanced" as const, label: "平衡", desc: "預設；語意相關即可" },
  { id: "exploratory" as const, label: "探索", desc: "較寬鬆，適合發想人脈（Pro）" },
];

export function SettingsPage() {
  const { data: me, isLoading } = useMe();
  const switchPlan = useSwitchPlan();
  const updateSettings = useUpdateSettings();
  const [error, setError] = useState<string | null>(null);

  if (isLoading || !me) {
    return (
      <div className="flex min-h-full items-center justify-center py-16 text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  const isPro = me.plan_tier === "pro" || me.plan_tier === "enterprise";
  const busy = switchPlan.isPending || updateSettings.isPending;

  const apply = (payload: SettingsPayload) => {
    setError(null);
    updateSettings.mutate(payload, {
      onError: (err) => setError(formatError(err)),
    });
  };

  return (
    <div className="mx-auto w-full max-w-xl space-y-4 px-4 py-5">
      <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">設定</h1>

      {/* 方案 */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">方案</h2>
            <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">
              目前：<span className="font-medium text-[var(--color-text-secondary)]">{planLabel(me.plan_tier)}</span>
            </p>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={() => switchPlan.mutate(isPro ? "free" : "pro")}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50",
              isPro
                ? "border border-[var(--color-border)] text-[var(--color-text-secondary)]"
                : "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]",
            )}
          >
            {isPro ? "改回 Free" : "試用 Pro"}
          </button>
        </div>
        {!isPro && (
          <p className="mt-3 text-xs text-[var(--color-text-secondary)]">
            Pro：公司資料自動保持最新、用 LinkedIn 公開資料補強職責、更高搜尋與更新額度。
          </p>
        )}
      </section>

      {/* 用量 */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">本期用量</h2>
        <dl className="mt-3 grid grid-cols-2 gap-3">
          <QuotaItem label="搜尋（今日剩）" value={me.quotas.search_cache_remaining_today} />
          <QuotaItem label="即時查（本月剩）" value={me.quotas.live_augment_remaining_month} />
          <QuotaItem label="更新公司（本月剩）" value={me.quotas.manual_refresh_remaining_month} />
          <QuotaItem label="LinkedIn 補充（本月剩）" value={me.quotas.person_linkedin_remaining_month} />
        </dl>
      </section>

      {/* AI 嚴格度 */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">AI 嚴格度</h2>
        <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">
          控制 AI 排序時要多嚴格；不影響每次搜尋的對話意圖解析
        </p>
        <div className="mt-3 space-y-2">
          {PRECISION_OPTIONS.map((opt) => {
            const locked = opt.id === "exploratory" && !me.search_precision.can_use_exploratory;
            const selected = me.search_precision.mode === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                disabled={busy || locked}
                onClick={() => !locked && apply({ search_precision: opt.id })}
                className={cn(
                  "w-full rounded-lg border px-3 py-2.5 text-left transition-colors disabled:opacity-50",
                  selected
                    ? "border-[var(--color-primary)] bg-[var(--color-ai-bg)]"
                    : "border-[var(--color-border)] hover:border-[var(--color-primary)]/40",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">
                    {opt.label}
                    {locked && (
                      <span className="ml-1.5 rounded bg-[var(--color-border)] px-1.5 py-0.5 text-[10px] font-normal text-[var(--color-text-tertiary)]">
                        Pro
                      </span>
                    )}
                  </span>
                  {selected && (
                    <span className="text-[10px] text-[var(--color-primary)]">使用中</span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{opt.desc}</p>
              </button>
            );
          })}
        </div>
        {!me.search_precision.can_use_exploratory && (
          <button
            type="button"
            disabled={busy}
            onClick={() => switchPlan.mutate("pro")}
            className="mt-3 text-xs font-medium text-[var(--color-primary)] hover:underline disabled:opacity-50"
          >
            升級 Pro 解鎖探索模式 →
          </button>
        )}
      </section>

      {/* Pro 設定 */}
      <section
        className={cn(
          "relative rounded-xl border p-4",
          isPro
            ? "border-[var(--color-border)] bg-[var(--color-surface)]"
            : "border-dashed border-[var(--color-border)] bg-[var(--color-surface)]",
        )}
      >
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">資料更新（Pro）</h2>

        <div className={cn("mt-3 space-y-4", !isPro && "pointer-events-none opacity-50")}>
          <ToggleRow
            title="公司資料過期自動更新"
            desc="背景定期重抓官網，讓公司產品資訊保持最新"
            checked={me.auto_refresh.enabled}
            disabled={busy || !isPro}
            onChange={(v) => apply({ auto_refresh_enabled: v })}
          />

          <div className={cn(!me.auto_refresh.enabled && "opacity-50")}>
            <p className="text-sm text-[var(--color-text-primary)]">更新頻率</p>
            <div className="mt-2 flex gap-2">
              {INTERVALS.map((d) => (
                <button
                  key={d}
                  type="button"
                  disabled={busy || !isPro || !me.auto_refresh.enabled}
                  onClick={() => apply({ auto_refresh_interval_days: d })}
                  className={cn(
                    "flex-1 rounded-lg border py-2 text-xs font-medium disabled:opacity-50",
                    me.auto_refresh.interval_days === d
                      ? "border-[var(--color-primary)] bg-[var(--color-ai-bg)] text-[var(--color-primary)]"
                      : "border-[var(--color-border)] text-[var(--color-text-secondary)]",
                  )}
                >
                  每 {d} 天
                </button>
              ))}
            </div>
          </div>

          <ToggleRow
            title="名片含 LinkedIn 時自動補充職責"
            desc="收錄到帶 LinkedIn 連結的名片時，背景自動整理職責（不佔手動額度）"
            checked={me.person_enrich.auto_on_url}
            disabled={busy || !isPro}
            onChange={(v) => apply({ person_linkedin_auto_on_url: v })}
          />
        </div>

        {!isPro && (
          <button
            type="button"
            disabled={busy}
            onClick={() => switchPlan.mutate("pro")}
            className="mt-4 w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
          >
            升級 Pro 解鎖
          </button>
        )}

        {error && <p className="mt-3 text-xs text-[var(--color-accent-hover)]">{error}</p>}
      </section>
    </div>
  );
}

function QuotaItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-[var(--color-bg)] px-3 py-2">
      <dd className="text-base font-semibold text-[var(--color-text-primary)]">{value}</dd>
      <dt className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">{label}</dt>
    </div>
  );
}

function ToggleRow({
  title,
  desc,
  checked,
  disabled,
  onChange,
}: {
  title: string;
  desc: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex-1">
        <p className="text-sm text-[var(--color-text-primary)]">{title}</p>
        <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{desc}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50",
          checked ? "bg-[var(--color-primary)]" : "bg-[var(--color-border)]",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform",
            checked ? "translate-x-[22px]" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}

function planLabel(tier: string): string {
  if (tier === "pro") return "Pro";
  if (tier === "enterprise") return "企業版";
  return "Free";
}

function formatError(err: unknown): string {
  const msg = err instanceof Error ? err.message : "";
  if (msg.includes("PRO_REQUIRED")) return "此設定需要 Pro 方案";
  if (msg.includes("SEARCH_PRECISION_NOT_ALLOWED")) return "探索模式需要 Pro 方案";
  if (msg.includes("INVALID_REFRESH_INTERVAL")) return "不支援的更新頻率";
  return "無法儲存設定，請稍後再試";
}
