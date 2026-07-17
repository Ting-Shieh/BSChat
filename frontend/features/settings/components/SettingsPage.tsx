"use client";

import { useState } from "react";
import Link from "next/link";
import { useLogout, useMe, useUpdateSettings } from "@/features/auth/hooks";
import type { SettingsPayload } from "@/features/auth/hooks";
import { useRouter } from "next/navigation";
import { cn } from "@/shared/lib/cn";
import { TeamInviteSection } from "./TeamInviteSection";

const INTERVALS = [30, 60, 90] as const;

const SEARCH_DAILY: Record<string, number> = { free: 30, pro: 50, enterprise: 100 };
const LIVE_MONTHLY: Record<string, number> = { free: 5, pro: 30, enterprise: 100 };

const PRECISION_OPTIONS = [
  { id: "strict" as const, label: "精準" },
  { id: "balanced" as const, label: "平衡" },
  { id: "exploratory" as const, label: "探索" },
];

const UPGRADE_MAIL =
  "mailto:hello@bschat.app?subject=" + encodeURIComponent("申請升級 BSChat Pro／企業版");

export function SettingsPage() {
  const router = useRouter();
  const { data: me, isLoading } = useMe();
  const updateSettings = useUpdateSettings();
  const logout = useLogout();
  const [error, setError] = useState<string | null>(null);

  if (isLoading || !me) {
    return (
      <div className="flex min-h-full items-center justify-center py-16 text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  const isPro = me.plan_tier === "pro" || me.plan_tier === "enterprise";
  const isEnterprise = me.plan_tier === "enterprise";
  const busy = updateSettings.isPending;
  const initials = (me.display_name ?? me.email ?? "?").slice(0, 2);
  const searchCap = SEARCH_DAILY[me.plan_tier] ?? 30;
  const liveCap = LIVE_MONTHLY[me.plan_tier] ?? 5;
  const searchUsed = Math.max(0, searchCap - me.quotas.search_cache_remaining_today);
  const liveUsed = Math.max(0, liveCap - me.quotas.live_augment_remaining_month);
  const publicLeft = me.quotas.public_recommend_remaining_lifetime ?? 0;

  const apply = (payload: SettingsPayload) => {
    setError(null);
    updateSettings.mutate(payload, {
      onError: (err) => setError(formatError(err)),
    });
  };

  return (
    <div className="mx-auto w-full max-w-xl space-y-4 px-4 py-5">
      <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">我的</h1>

      <section className="flex items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[11px] bg-[var(--color-primary-muted)] text-base font-bold text-[var(--color-primary)]">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-[var(--color-text-primary)]">
            {me.display_name ?? "使用者"}
          </p>
          <p className="truncate font-mono text-[11.5px] text-[var(--color-text-secondary)]">
            {me.email}
          </p>
        </div>
        <span className="rounded-full bg-[#F5F5F4] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-text-secondary)]">
          {planLabel(me.plan_tier)}
        </span>
      </section>

      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        本期用量
      </p>
      <section className="-mt-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5">
        <QuotaBar label="對話搜尋" used={searchUsed} cap={searchCap} unit="日" />
        <div className="mt-3">
          <QuotaBar label="即時上網查" used={liveUsed} cap={liveCap} unit="月" />
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-2 border-t border-[var(--color-border)] pt-3">
          <MiniQuota label="更新公司（剩）" value={me.quotas.manual_refresh_remaining_month} />
          <MiniQuota label="LinkedIn（剩）" value={me.quotas.person_linkedin_remaining_month} />
        </dl>
        <div className="mt-3 border-t border-[var(--color-border)] pt-3">
          {me.quotas.public_recommend_unlimited ? (
            <div className="rounded-lg bg-[var(--color-bg)] px-3 py-2">
              <p className="text-base font-semibold text-[var(--color-text-primary)]">無限</p>
              <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">公開推薦 · 方案內</p>
            </div>
          ) : (
            <div className="rounded-lg bg-[var(--color-bg)] px-3 py-2">
              <p className="text-base font-semibold text-[var(--color-text-primary)]">
                {publicLeft > 0 ? `剩 ${publicLeft}／2` : "已用完"}
              </p>
              <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">
                公開推薦試用 · 終身 · 不按月重置
              </p>
            </div>
          )}
        </div>
      </section>

      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">方案</p>
      <section className="-mt-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5">
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">
          目前：{planLabel(me.plan_tier)}
        </p>
        <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--color-text-secondary)]">
          {me.plan_tier === "free" && "庫內搜尋＋Plan · 公開推薦終身 2 次"}
          {me.plan_tier === "pro" && "可搜公開推薦池。對外曝光電子名片請申請企業版。"}
          {me.plan_tier === "enterprise" && "公開推薦無限 · 可管理電子名片與允許 AI 推薦"}
        </p>
        <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-[11.5px] leading-relaxed text-amber-900">
          產品不提供一鍵切換方案。升級請走下方申請。
        </p>
      </section>

      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        搜尋偏好 · 精準度
      </p>
      <section className="-mt-2">
        <div className="flex rounded-[10px] bg-[#F5F5F4] p-0.5">
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
                  "flex-1 rounded-lg py-2 text-center text-[12.5px] disabled:opacity-50",
                  selected
                    ? "bg-white font-semibold text-[var(--color-primary)] shadow-sm"
                    : "text-[var(--color-text-secondary)]",
                  locked && "text-[var(--color-text-tertiary)]",
                )}
              >
                {opt.label}
                {locked ? " 🔒" : ""}
              </button>
            );
          })}
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--color-text-tertiary)]">
          「探索」放寬匹配並可搜公開商務池
          {!me.search_precision.can_use_exploratory && (
            <>
              {" "}
              ——{" "}
              <a href={UPGRADE_MAIL} className="text-[var(--color-info)]">
                申請升級
              </a>
            </>
          )}
        </p>
      </section>

      <p className="text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        資料與隱私
      </p>
      <div className="-mt-2 rounded-xl bg-[var(--color-privacy-bg)] px-3 py-3 text-[12.5px] leading-relaxed text-[var(--color-privacy-text)]">
        🔒 私有收錄永不被外人搜到。團隊池僅同公司可見。公開推薦僅企業電子名片 opt-in。
        {me.org_memberships && me.org_memberships.length > 0 && (
          <span className="mt-1 block opacity-90">
            目前團隊：{me.org_memberships.map((o) => o.org_name).join("、")}
          </span>
        )}
      </div>

      <TeamInviteSection />

      {isPro && (
        <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">資料更新（Pro）</h2>
          <div className="mt-3 space-y-4">
            <ToggleRow
              title="公司資料過期自動更新"
              desc="背景定期重抓官網"
              checked={me.auto_refresh.enabled}
              disabled={busy}
              onChange={(v) => apply({ auto_refresh_enabled: v })}
            />
            <div className={cn(!me.auto_refresh.enabled && "opacity-50")}>
              <p className="text-sm text-[var(--color-text-primary)]">更新頻率</p>
              <div className="mt-2 flex gap-2">
                {INTERVALS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    disabled={busy || !me.auto_refresh.enabled}
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
              title="含 LinkedIn 時自動補充職責"
              desc="收錄帶 LinkedIn 的名片時背景整理"
              checked={me.person_enrich.auto_on_url}
              disabled={busy}
              onChange={(v) => apply({ person_linkedin_auto_on_url: v })}
            />
          </div>
          {error && <p className="mt-3 text-xs text-[var(--color-accent-hover)]">{error}</p>}
        </section>
      )}

      {!isPro && (
        <div className="rounded-[14px] bg-gradient-to-r from-[var(--color-primary)] to-[#12657a] p-4 text-white">
          <p className="text-[15px] font-semibold">需要更多公開推薦？</p>
          <p className="mt-1 text-xs leading-relaxed opacity-85">
            升級 Pro：公開推薦無限 · LinkedIn 補充 · 資料自動更新
          </p>
          <a
            href={UPGRADE_MAIL}
            className="mt-3 block w-full rounded-lg bg-white py-2.5 text-center text-sm font-semibold text-[var(--color-primary)]"
          >
            聯絡我們升級 Pro
          </a>
        </div>
      )}

      {!isEnterprise && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
          <p className="text-sm font-medium text-[var(--color-text-primary)]">要被 AI 推薦給外人？</p>
          <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--color-text-secondary)]">
            公開曝光電子名片為企業版功能，請由公司管理員邀請你加入企業租戶。
          </p>
        </div>
      )}

      {isEnterprise && (
        <Link
          href="/admin/org"
          className="block rounded-xl border border-[var(--color-primary)] bg-[var(--color-surface)] px-4 py-3 text-center text-sm font-medium text-[var(--color-primary)]"
        >
          {me.org_memberships?.some((o) => o.is_primary_admin)
            ? "企業後台（名片／成員）→"
            : "電子名片管理 →"}
        </Link>
      )}

      <button
        type="button"
        onClick={() => {
          void logout().then(() => router.push("/login"));
        }}
        className="w-full py-2 text-sm text-[var(--color-text-tertiary)]"
      >
        登出
      </button>
    </div>
  );
}

function QuotaBar({
  label,
  used,
  cap,
  unit,
}: {
  label: string;
  used: number;
  cap: number;
  unit: string;
}) {
  const pct = cap > 0 ? Math.min(100, Math.round((used / cap) * 100)) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-[12.5px]">
        <span>{label}</span>
        <span className="font-mono text-[var(--color-text-secondary)]">
          {used} / {cap} {unit}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#F5F5F4]">
        <div className="h-full rounded-full bg-[var(--color-primary)]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function MiniQuota({ label, value }: { label: string; value: number }) {
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
