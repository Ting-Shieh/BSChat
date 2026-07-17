"use client";

import { useState } from "react";
import {
  useCreateEnterpriseInvite,
  useEnterpriseInvites,
  useEnterpriseMembers,
  useRemoveEnterpriseMember,
  useRevokeEnterpriseInvite,
  useTransferEnterpriseAdmin,
} from "@/features/enterprise/hooks";

export function EnterpriseRosterPanel({ orgId }: { orgId: string }) {
  const { data: members, isLoading: membersLoading } = useEnterpriseMembers(orgId);
  const { data: invites, isLoading: invitesLoading } = useEnterpriseInvites(orgId);
  const createInvite = useCreateEnterpriseInvite(orgId);
  const removeMember = useRemoveEnterpriseMember(orgId);
  const revokeInvite = useRevokeEnterpriseInvite(orgId);
  const transfer = useTransferEnterpriseAdmin(orgId);

  const [email, setEmail] = useState("");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [inviteStatus, setInviteStatus] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transferUserId, setTransferUserId] = useState("");

  const busy =
    createInvite.isPending ||
    removeMember.isPending ||
    revokeInvite.isPending ||
    transfer.isPending;

  return (
    <div className="mt-4 space-y-6">
      <section>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">成員</h2>
        {membersLoading ? (
          <p className="mt-2 text-xs text-[var(--color-text-secondary)]">載入中…</p>
        ) : (
          <ul className="mt-2 divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
            {(members || []).map((m) => (
              <li key={m.user_id} className="flex items-center justify-between gap-2 px-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm text-[var(--color-text-primary)]">
                    {m.display_name || m.email}
                    {m.is_primary_admin && (
                      <span className="ml-2 text-[10px] text-[var(--color-primary)]">主 Admin</span>
                    )}
                  </p>
                  <p className="truncate text-[11px] text-[var(--color-text-tertiary)]">{m.email}</p>
                </div>
                {!m.is_primary_admin && (
                  <button
                    type="button"
                    disabled={busy}
                    className="shrink-0 text-xs text-red-600 disabled:opacity-50"
                    onClick={() => {
                      if (!confirm(`移除 ${m.email}？對方將失去企業能力，公開名片會下架。`)) return;
                      setError(null);
                      removeMember.mutate(m.user_id, {
                        onError: (e) => setError(e instanceof Error ? e.message : "移除失敗"),
                      });
                    }}
                  >
                    移除
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">邀請成員</h2>
        <div className="mt-2 flex gap-2">
          <input
            type="email"
            className="min-w-0 flex-1 rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
            placeholder="業務 Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button
            type="button"
            disabled={busy || !email.trim()}
            className="shrink-0 rounded-lg bg-[var(--color-primary)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            onClick={() => {
              setError(null);
              setInviteUrl(null);
              setInviteStatus(null);
              createInvite.mutate(
                { email: email.trim() },
                {
                  onSuccess: (res) => {
                    setInviteUrl(`${window.location.origin}${res.join_path}`);
                    setInviteStatus(
                      res.email_sent
                        ? `邀請信已寄到 ${res.invited_email}`
                        : "邀請已建立，但寄信服務尚未設定或寄送失敗；請複製連結傳給對方。",
                    );
                    setEmail("");
                  },
                  onError: (e) => setError(e instanceof Error ? e.message : "邀請失敗"),
                },
              );
            }}
          >
            邀請
          </button>
        </div>
        {inviteUrl && (
          <div className="mt-2 rounded-lg bg-[var(--color-ai-bg)] p-3">
            {inviteStatus && (
              <p className="text-xs text-[var(--color-text-secondary)]">{inviteStatus}</p>
            )}
            <p className="mt-2 break-all font-mono text-[11px] text-[var(--color-text-secondary)]">
              {inviteUrl}
            </p>
            <button
              type="button"
              className="mt-2 text-xs font-semibold text-[var(--color-primary)]"
              onClick={async () => {
                await navigator.clipboard.writeText(inviteUrl);
                setCopied(true);
                window.setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? "已複製" : "複製邀請連結"}
            </button>
          </div>
        )}
        {invitesLoading ? null : (
          <ul className="mt-3 space-y-1">
            {(invites || [])
              .filter((i) => !i.revoked_at && i.use_count < i.max_uses)
              .map((i) => (
                <li
                  key={i.invite_id}
                  className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]"
                >
                  <span>{i.invited_email}</span>
                  <button
                    type="button"
                    disabled={busy}
                    className="text-red-600 disabled:opacity-50"
                    onClick={() => revokeInvite.mutate(i.invite_id)}
                  >
                    撤銷
                  </button>
                </li>
              ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">轉移主 Admin</h2>
        <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
          轉移後你將失去主 Admin；請先確認對方已在成員名單中。
        </p>
        <select
          className="mt-2 w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          value={transferUserId}
          onChange={(e) => setTransferUserId(e.target.value)}
        >
          <option value="">選擇成員…</option>
          {(members || [])
            .filter((m) => !m.is_primary_admin)
            .map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.display_name || m.email}
              </option>
            ))}
        </select>
        <button
          type="button"
          disabled={busy || !transferUserId}
          className="mt-2 w-full rounded-lg border border-[var(--color-border)] py-2 text-sm font-semibold disabled:opacity-50"
          onClick={() => {
            if (!confirm("確定轉移主 Admin？你將失去管理權。")) return;
            setError(null);
            transfer.mutate(transferUserId, {
              onError: (e) => setError(e instanceof Error ? e.message : "轉移失敗"),
            });
          }}
        >
          確認轉移
        </button>
      </section>

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
