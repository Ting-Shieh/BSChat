"use client";

import { useState } from "react";
import { useCreateInvite, useCreateTeam, useMe } from "@/features/auth/hooks";

export function TeamInviteSection() {
  const { data: me, isLoading } = useMe();
  const createTeam = useCreateTeam();
  const createInvite = useCreateInvite();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (isLoading || !me) return null;

  const orgs = me.org_memberships || [];
  const primary = orgs.find((o) => !o.is_enterprise) || orgs[0];
  const enterpriseOnly = orgs.length > 0 && orgs.every((o) => o.is_enterprise);

  if (enterpriseOnly) {
    return (
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">企業成員邀請</h2>
        <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
          企業席次請到「企業後台 → 成員」由主 Admin 邀請。
        </p>
      </section>
    );
  }

  async function handleCreateTeam() {
    setError(null);
    try {
      await createTeam.mutateAsync({ name: name.trim(), slug: slug.trim() });
      setName("");
      setSlug("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "建立失敗");
    }
  }

  async function handleCreateInvite() {
    if (!primary) return;
    setError(null);
    setInviteUrl(null);
    try {
      const res = await createInvite.mutateAsync({ org_id: primary.org_id });
      const url = `${window.location.origin}${res.join_path}`;
      setInviteUrl(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "產生邀請失敗");
    }
  }

  async function copyLink() {
    if (!inviteUrl) return;
    await navigator.clipboard.writeText(inviteUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <h2 className="text-sm font-medium text-[var(--color-text-primary)]">團隊邀請</h2>
      <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
        邀請連結決定進哪個團隊；登入身分由 Google／公司信箱驗證。
      </p>

      {primary ? (
        <div className="mt-3 space-y-3">
          <p className="text-sm text-[var(--color-text-primary)]">
            目前團隊：<span className="font-semibold">{primary.org_name}</span>
          </p>
          <button
            type="button"
            disabled={createInvite.isPending}
            onClick={() => void handleCreateInvite()}
            className="w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {createInvite.isPending ? "產生中…" : "產生邀請連結"}
          </button>
          {inviteUrl && (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-ai-bg)] p-3">
              <p className="break-all font-mono text-[11px] text-[var(--color-text-secondary)]">
                {inviteUrl}
              </p>
              <button
                type="button"
                onClick={() => void copyLink()}
                className="mt-2 text-xs font-semibold text-[var(--color-primary)]"
              >
                {copied ? "已複製" : "複製連結"}
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-[var(--color-text-secondary)]">你還沒有團隊，先建立一個：</p>
          <input
            className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
            placeholder="團隊名稱"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
            placeholder="代號（英文，如 acme-team）"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
          />
          <button
            type="button"
            disabled={createTeam.isPending || !name.trim() || !slug.trim()}
            onClick={() => void handleCreateTeam()}
            className="w-full rounded-lg border border-[var(--color-primary)] py-2.5 text-sm font-semibold text-[var(--color-primary)] disabled:opacity-50"
          >
            {createTeam.isPending ? "建立中…" : "建立團隊"}
          </button>
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </section>
  );
}
