"use client";

import { useMemo, useState } from "react";
import {
  useCreateEnterpriseInvite,
  useCreateEnterpriseInviteBatch,
  useEnterpriseInvites,
  useEnterpriseMembers,
  useRegenerateEnterpriseInviteLink,
  useRemoveEnterpriseMember,
  useRevokeEnterpriseInvite,
  useTransferEnterpriseAdmin,
} from "@/features/enterprise/hooks";
import type { EnterpriseInviteItem, EnterpriseMember } from "@/features/enterprise/api";
import {
  useCreateStub,
  useImportStubsCsv,
  useOrgStubs,
  usePublishStub,
  useUnpublishStub,
  useUpdateStub,
} from "@/features/org/hooks";
import type { PublicStub } from "@/features/org/api";
import { cn } from "@/shared/lib/cn";
import { formatApiError } from "@/shared/lib/api-client";

type AiState = "on" | "off" | "none" | "pending" | "pending_url";

function normalizePublicUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function parseEmails(raw: string): string[] {
  const parts = raw
    .split(/[\n,;]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(parts)];
}

function aiStateForMember(
  member: EnterpriseMember,
  stubsByOwner: Map<string, PublicStub>,
): AiState {
  const stub = stubsByOwner.get(member.user_id);
  if (!stub) return "none";
  if (stub.status === "published") return "on";
  if (stub.want_ai_recommend !== false && !(stub.external_card_url || "").trim()) {
    return "pending_url";
  }
  return "off";
}

function AiLabel({ state }: { state: AiState }) {
  if (state === "pending") {
    return <span className="text-[10px] text-[var(--color-text-tertiary)]">不可曝光（邀請中）</span>;
  }
  if (state === "pending_url") {
    return <span className="text-[10px] font-medium text-amber-700">AI 預設開 · 待補名片</span>;
  }
  if (state === "on") {
    return <span className="text-[10px] font-medium text-green-700">AI 推薦：已曝光</span>;
  }
  if (state === "off") {
    return <span className="text-[10px] text-amber-700">AI 推薦：關</span>;
  }
  return <span className="text-[10px] text-[var(--color-text-tertiary)]">AI 推薦：未設定</span>;
}

export function EnterpriseRosterPanel({
  orgId,
  orgName,
}: {
  orgId: string;
  orgName: string;
}) {
  const { data: members, isLoading: membersLoading } = useEnterpriseMembers(orgId);
  const { data: invites, isLoading: invitesLoading } = useEnterpriseInvites(orgId);
  const { data: stubsData } = useOrgStubs(orgId);
  const createInvite = useCreateEnterpriseInvite(orgId);
  const createBatch = useCreateEnterpriseInviteBatch(orgId);
  const removeMember = useRemoveEnterpriseMember(orgId);
  const revokeInvite = useRevokeEnterpriseInvite(orgId);
  const regenerateLink = useRegenerateEnterpriseInviteLink(orgId);
  const transfer = useTransferEnterpriseAdmin(orgId);
  const createStub = useCreateStub(orgId);
  const updateStub = useUpdateStub(orgId);
  const publishStub = usePublishStub(orgId);
  const unpublishStub = useUnpublishStub(orgId);
  const importCsv = useImportStubsCsv(orgId);

  const [query, setQuery] = useState("");
  const [email, setEmail] = useState("");
  const [batchEmails, setBatchEmails] = useState("");
  const [showBatch, setShowBatch] = useState(false);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [inviteStatus, setInviteStatus] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transferUserId, setTransferUserId] = useState("");
  const [showTransfer, setShowTransfer] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [externalUrl, setExternalUrl] = useState("");
  const [title, setTitle] = useState("");

  const stubsByOwner = useMemo(() => {
    const map = new Map<string, PublicStub>();
    for (const s of stubsData?.items ?? []) {
      if (s.owner_user_id) map.set(s.owner_user_id, s);
    }
    return map;
  }, [stubsData]);

  const pendingInvites = useMemo(
    () => (invites || []).filter((i) => !i.revoked_at && i.use_count < i.max_uses),
    [invites],
  );

  type Row =
    | { kind: "member"; member: EnterpriseMember }
    | { kind: "invite"; invite: EnterpriseInviteItem };

  const rows: Row[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    const memberRows: Row[] = (members || []).map((m) => ({ kind: "member", member: m }));
    const inviteRows: Row[] = pendingInvites.map((i) => ({ kind: "invite", invite: i }));
    const all = [...memberRows, ...inviteRows];
    if (!q) return all;
    return all.filter((r) => {
      if (r.kind === "member") {
        return (
          r.member.email.toLowerCase().includes(q) ||
          (r.member.display_name || "").toLowerCase().includes(q)
        );
      }
      return (r.invite.invited_email || "").toLowerCase().includes(q);
    });
  }, [members, pendingInvites, query]);

  const busy =
    createInvite.isPending ||
    createBatch.isPending ||
    removeMember.isPending ||
    revokeInvite.isPending ||
    regenerateLink.isPending ||
    transfer.isPending ||
    createStub.isPending ||
    updateStub.isPending ||
    publishStub.isPending ||
    unpublishStub.isPending ||
    importCsv.isPending;

  const startEnableAi = (m: EnterpriseMember) => {
    const stub = stubsByOwner.get(m.user_id);
    setEditingUserId(m.user_id);
    setExternalUrl(stub?.external_card_url ?? "");
    setTitle(stub?.title ?? "");
    setError(null);
  };

  const submitEnableAi = (m: EnterpriseMember) => {
    const url = normalizePublicUrl(externalUrl);
    if (!url) {
      setError("請填對方的名片連結（LinkedIn／個人頁／既有名片商頁）");
      return;
    }
    setError(null);
    const existing = stubsByOwner.get(m.user_id);
    if (existing) {
      updateStub.mutate(
        {
          stubId: existing.id,
          body: {
            display_name: m.display_name || m.email,
            company_name: orgName,
            title: title.trim() || null,
            external_card_url: url,
            owner_user_id: m.user_id,
            want_ai_recommend: true,
          },
        },
        {
          onSuccess: () => setEditingUserId(null),
          onError: (e) => setError(e.message),
        },
      );
      return;
    }
    createStub.mutate(
      {
        display_name: m.display_name || m.email,
        company_name: orgName,
        title: title.trim() || null,
        external_card_url: url,
        allow_ai_recommend: true,
        owner_user_id: m.user_id,
      },
      {
        onSuccess: () => setEditingUserId(null),
        onError: (e) => setError(e.message),
      },
    );
  };

  const turnOffAi = (m: EnterpriseMember) => {
    const stub = stubsByOwner.get(m.user_id);
    if (!stub) return;
    if (stub.status === "published") {
      unpublishStub.mutate(stub.id, {
        onError: (e) => setError(e.message),
      });
      return;
    }
    updateStub.mutate(
      {
        stubId: stub.id,
        body: { want_ai_recommend: false },
      },
      { onError: (e) => setError(e.message) },
    );
  };

  const onCount = (members || []).filter((m) => aiStateForMember(m, stubsByOwner) === "on").length;
  const pendingUrlCount = (members || []).filter(
    (m) => aiStateForMember(m, stubsByOwner) === "pending_url",
  ).length;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2.5">
        <p className="text-xs text-[var(--color-text-secondary)]">
          一個列表看全公司：邀請狀態與 AI 推薦。mail＝帳號＝人；邀請中不可曝光。
        </p>
        <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
          已加入 {members?.length ?? "…"} · 邀請中 {pendingInvites.length} · 已曝光 {onCount}
          {pendingUrlCount > 0 ? ` · 待補名片 ${pendingUrlCount}` : ""}
        </p>
      </div>

      <section>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">邀請成員</h2>
        <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
          用公司規定 Email 邀請；對方加入後自動建立公開身份（AI 預設開，待補名片連結）。
        </p>
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
                        : "邀請已建立，但信沒寄出。請複製下方連結傳給對方。",
                    );
                    setEmail("");
                  },
                  onError: (e) => setError(formatApiError(e, "邀請失敗")),
                },
              );
            }}
          >
            邀請
          </button>
        </div>
        <button
          type="button"
          className="mt-2 text-xs text-[var(--color-primary)]"
          onClick={() => setShowBatch((v) => !v)}
        >
          {showBatch ? "收合批次邀請" : "批次邀請（多個 Email）…"}
        </button>
        {showBatch && (
          <div className="mt-2 space-y-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-3">
            <textarea
              value={batchEmails}
              onChange={(e) => setBatchEmails(e.target.value)}
              rows={4}
              placeholder={"一行一個，或用逗號分隔\na@corp.com\nb@corp.com"}
              className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 font-mono text-xs"
            />
            <button
              type="button"
              disabled={busy || parseEmails(batchEmails).length === 0}
              className="w-full rounded-lg bg-[var(--color-primary)] py-2 text-sm font-semibold text-white disabled:opacity-50"
              onClick={() => {
                const emails = parseEmails(batchEmails);
                setError(null);
                setInviteStatus(null);
                createBatch.mutate(
                  { emails },
                  {
                    onSuccess: (res) => {
                      setInviteStatus(
                        `批次完成：建立 ${res.created}、略過 ${res.skipped}` +
                          (res.items.some((i) => i.status === "created" && !i.email_sent)
                            ? "（部分未寄信，可於邀請列表撤銷後重邀）"
                            : ""),
                      );
                      setBatchEmails("");
                    },
                    onError: (e) => setError(formatApiError(e, "批次邀請失敗")),
                  },
                );
              }}
            >
              送出批次邀請（{parseEmails(batchEmails).length}）
            </button>
          </div>
        )}
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
        {!inviteUrl && inviteStatus && (
          <p className="mt-2 text-xs text-[var(--color-text-secondary)]">{inviteStatus}</p>
        )}
      </section>

      <div className="flex flex-wrap gap-2">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋姓名或 Email"
          className="min-w-0 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
        />
        <button
          type="button"
          className="rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)]"
          onClick={() => setShowImport((v) => !v)}
        >
          匯入
        </button>
      </div>

      {showImport && (
        <section className="rounded-lg border border-[var(--color-border)] p-3">
          <p className="text-[11px] text-[var(--color-text-tertiary)]">
            CSV（進階）：建議以邀請＋成員列補名片連結為主。表頭含 display_name, company_name,
            external_card_url…
          </p>
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={busy}
            className="mt-2 block w-full text-sm"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setImportResult(null);
              importCsv.mutate(
                { file, autoPublish: false },
                {
                  onSuccess: (r) =>
                    setImportResult(`匯入 ${r.imported} 筆草稿，略過 ${r.skipped}（需再綁帳號才能曝光）`),
                  onError: (err) => setImportResult(err.message),
                },
              );
              e.target.value = "";
            }}
          />
          {importResult && (
            <p className="mt-2 text-xs text-[var(--color-text-secondary)]">{importResult}</p>
          )}
        </section>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}

      {membersLoading || invitesLoading ? (
        <p className="text-xs text-[var(--color-text-secondary)]">載入中…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">尚無成員或邀請</p>
      ) : (
        <ul className="max-h-[min(65vh,32rem)] divide-y divide-[var(--color-border)] overflow-y-auto rounded-lg border border-[var(--color-border)]">
          {rows.map((row) => {
            if (row.kind === "invite") {
              const i = row.invite;
              return (
                <li
                  key={`inv-${i.invite_id}`}
                  className="flex items-center justify-between gap-2 bg-[var(--color-surface)] px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-[var(--color-text-primary)]">
                      {i.invited_email}
                    </p>
                    <p className="text-[10px] text-amber-700">狀態：邀請中</p>
                    <AiLabel state="pending" />
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <button
                      type="button"
                      disabled={busy || regenerateLink.isPending}
                      className="text-xs font-semibold text-[var(--color-primary)] disabled:opacity-50"
                      onClick={() => {
                        setError(null);
                        regenerateLink.mutate(i.invite_id, {
                          onSuccess: async (res) => {
                            const url = `${window.location.origin}${res.join_path}`;
                            setInviteUrl(url);
                            setInviteStatus(
                              `已產生 ${res.invited_email || "邀請"} 的連結（舊連結失效）。請複製傳給對方。`,
                            );
                            try {
                              await navigator.clipboard.writeText(url);
                              setCopied(true);
                              window.setTimeout(() => setCopied(false), 1500);
                            } catch {
                              /* clipboard may be blocked; URL box still shown */
                            }
                            window.scrollTo({ top: 0, behavior: "smooth" });
                          },
                          onError: (e) => setError(formatApiError(e, "無法產生連結")),
                        });
                      }}
                    >
                      複製連結
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="text-xs text-red-600 disabled:opacity-50"
                      onClick={() => revokeInvite.mutate(i.invite_id)}
                    >
                      撤銷
                    </button>
                  </div>
                </li>
              );
            }

            const m = row.member;
            const state = aiStateForMember(m, stubsByOwner);
            const isEditing = editingUserId === m.user_id;

            return (
              <li key={m.user_id} className="bg-[var(--color-surface)] px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-[var(--color-text-primary)]">
                      {m.display_name || m.email}
                      {m.is_primary_admin && (
                        <span className="ml-2 text-[10px] text-[var(--color-primary)]">主 Admin</span>
                      )}
                    </p>
                    <p className="truncate text-[11px] text-[var(--color-text-tertiary)]">{m.email}</p>
                    <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">狀態：已加入</p>
                    <AiLabel state={state} />
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    {(state === "on" || state === "pending_url") && (
                      <button
                        type="button"
                        disabled={busy}
                        className="text-xs text-[var(--color-text-secondary)] disabled:opacity-50"
                        onClick={() => turnOffAi(m)}
                      >
                        關閉 AI
                      </button>
                    )}
                    {(state === "off" || state === "none" || state === "pending_url") && (
                      <button
                        type="button"
                        disabled={busy}
                        className={cn(
                          "text-xs font-medium disabled:opacity-50",
                          state === "pending_url"
                            ? "text-amber-700"
                            : "text-[var(--color-primary)]",
                        )}
                        onClick={() => startEnableAi(m)}
                      >
                        {state === "pending_url"
                          ? "補名片"
                          : state === "none"
                            ? "開啟 AI 推薦"
                            : "再次開啟"}
                      </button>
                    )}
                    {state === "on" && (
                      <button
                        type="button"
                        disabled={busy}
                        className="text-xs text-[var(--color-text-secondary)] disabled:opacity-50"
                        onClick={() => startEnableAi(m)}
                      >
                        編輯名片
                      </button>
                    )}
                    {!m.is_primary_admin && (
                      <button
                        type="button"
                        disabled={busy}
                        className="text-xs text-red-600 disabled:opacity-50"
                        onClick={() => {
                          if (!confirm(`移除 ${m.email}？將失去企業能力並下架公開身份。`)) return;
                          removeMember.mutate(m.user_id, {
                            onError: (e) => setError(formatApiError(e, "移除失敗")),
                          });
                        }}
                      >
                        移除
                      </button>
                    )}
                  </div>
                </div>
                {isEditing && (
                  <div className="mt-3 space-y-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-3">
                    <p className="text-[11px] text-[var(--color-text-tertiary)]">
                      Admin 或本人皆可補「自己的名片」連結；有名片且 AI 開才會曝光。
                    </p>
                    <label className="block text-xs">
                      <span className="text-[var(--color-text-secondary)]">職稱（選填）</span>
                      <input
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="block text-xs">
                      <span className="text-[var(--color-text-secondary)]">名片連結（必填）</span>
                      <input
                        value={externalUrl}
                        onChange={(e) => setExternalUrl(e.target.value)}
                        placeholder="https://www.linkedin.com/in/… 或個人／名片商頁"
                        className="mt-1 w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => submitEnableAi(m)}
                        className="flex-1 rounded-lg bg-[var(--color-primary)] py-2 text-sm font-medium text-white disabled:opacity-50"
                      >
                        儲存並開啟 AI
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => setEditingUserId(null)}
                        className="rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <div>
        <button
          type="button"
          className="text-xs text-[var(--color-text-tertiary)] underline"
          onClick={() => setShowTransfer((v) => !v)}
        >
          {showTransfer ? "收合設定" : "轉移主 Admin…"}
        </button>
        {showTransfer && (
          <section className="mt-2 rounded-lg border border-[var(--color-border)] p-3">
            <p className="text-[11px] text-[var(--color-text-tertiary)]">
              轉移後你將失去主 Admin。
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
                if (!confirm("確定轉移主 Admin？")) return;
                transfer.mutate(transferUserId, {
                  onError: (e) => setError(formatApiError(e, "轉移失敗")),
                });
              }}
            >
              確認轉移
            </button>
          </section>
        )}
      </div>
    </div>
  );
}
