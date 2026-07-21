"use client";

import { useMemo, useState } from "react";
import { useMe } from "@/features/auth/hooks";
import { useMyOrgs } from "@/features/org/hooks";
import { EnterpriseRosterPanel } from "@/features/enterprise/components/EnterpriseRosterPanel";

/**
 * Enterprise admin — DDR-v4-15: single「成員」surface.
 * Invite status + AI recommend live on one people list (no parallel 列表 tab).
 */
export function OrgAdminPage() {
  const { data: me } = useMe();
  const { data: orgs, isLoading: orgsLoading } = useMyOrgs();
  const [orgId, setOrgId] = useState<string | null>(null);

  const activeOrgId = orgId ?? orgs?.items[0]?.id ?? null;
  const isEnterprise = me?.plan_tier === "enterprise";
  const isPrimaryAdmin = Boolean(
    me?.org_memberships?.some((o) => o.org_id === activeOrgId && o.is_primary_admin),
  );

  const activeOrg = useMemo(
    () => orgs?.items.find((o) => o.id === activeOrgId),
    [orgs, activeOrgId],
  );

  if (!me || orgsLoading) {
    return (
      <div className="flex min-h-full items-center justify-center py-16 text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  if (!isEnterprise) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8">
        <h1 className="text-lg font-semibold">企業後台</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          管理成員與 AI 推薦需要<strong className="font-medium">企業版</strong>
          。請由公司管理員邀請你加入企業租戶。
        </p>
      </div>
    );
  }

  if (!activeOrgId || !orgs?.items.length) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8">
        <h1 className="text-lg font-semibold">企業後台</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          尚未加入任何組織。
        </p>
      </div>
    );
  }

  if (!isPrimaryAdmin) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8">
        <h1 className="text-lg font-semibold">企業後台</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          成員與 AI 推薦由主 Admin 管理。你目前是企業成員。
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col px-4 pb-5 pt-4">
      <div className="shrink-0">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">企業後台</h1>
        {activeOrg && (
          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
            {activeOrg.name} · 成員與 AI 推薦
          </p>
        )}
      </div>

      {orgs.items.length > 1 && (
        <select
          value={activeOrgId}
          onChange={(e) => setOrgId(e.target.value)}
          className="mt-3 w-full shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
        >
          {orgs.items.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      )}

      <div className="mt-4 min-h-0 flex-1">
        <EnterpriseRosterPanel orgId={activeOrgId} orgName={activeOrg?.name ?? ""} />
      </div>
    </div>
  );
}
