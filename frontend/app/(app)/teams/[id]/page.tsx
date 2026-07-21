"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  useCreateSubTeamInvite,
  useDissolveSubTeam,
  useLeaveSubTeam,
  useRemoveSubTeamMember,
  useRevokeSubTeamInvite,
  useSubTeam,
  useSubTeamInvites,
} from "@/features/subteam/hooks";
import type { SubTeamInviteStatus } from "@/features/subteam/api";
import { ApiError } from "@/shared/lib/api-client";

const STATUS_LABEL: Record<SubTeamInviteStatus, string> = {
  pending: "邀請中",
  accepted: "已加入",
  revoked: "已撤銷",
  expired: "已過期",
};

const ERR_HINT: Record<string, string> = {
  NOT_ORG_MEMBER: "對方須先是本企業成員（請主 Admin 先發企業邀請）",
  NOT_OWNER: "只有負責人可以邀請",
  ALREADY_MEMBER: "對方已在此子團隊",
  PENDING_EXISTS: "已有待接受邀請",
  INVALID_EMAIL: "Email 格式不正確",
};

function errorCode(err: unknown): string {
  if (!(err instanceof ApiError)) return "邀請失敗";
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    /* plain text */
  }
  return err.message;
}

export default function SubTeamDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { data, isLoading, isError } = useSubTeam(id);
  const isOwner = data?.my_role === "owner";
  const { data: invites } = useSubTeamInvites(id, Boolean(isOwner));
  const invite = useCreateSubTeamInvite(id);
  const revoke = useRevokeSubTeamInvite(id);
  const leave = useLeaveSubTeam(id);
  const dissolve = useDissolveSubTeam(id);
  const remove = useRemoveSubTeamMember(id);
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8 text-sm text-[var(--color-text-secondary)]">
        找不到子團隊或無權限。{" "}
        <Link href="/settings?tab=teams" className="text-[var(--color-primary)]">
          返回
        </Link>
      </div>
    );
  }

  const origin = typeof window !== "undefined" ? window.location.origin : "";

  return (
    <div className="mx-auto w-full max-w-xl px-4 py-5">
      <div className="mb-4 flex items-center gap-2">
        <Link href="/settings?tab=teams" className="text-[var(--color-primary)]">
          ‹
        </Link>
        <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">{data.name}</h1>
          <p className="text-[11.5px] text-[var(--color-text-tertiary)]">
            {data.org_name} · {data.member_count} 人
          </p>
        </div>
      </div>

      {isOwner && (
        <>
          <div className="mb-3 rounded-xl bg-[var(--color-primary-muted)] px-3 py-2.5 text-[12.5px] text-[var(--color-primary)]">
            你是負責人。用 Email 邀請已是企業成員的同事；對方會收到站內通知與邀請信。
          </div>

          <section className="mb-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <h2 className="text-sm font-medium">邀請成員</h2>
            <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
              一 Email 一邀請。對方須已在企業租戶內。
            </p>
            <div className="mt-2 flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="h-10 min-w-0 flex-1 rounded-lg border border-[var(--color-border)] px-3 text-sm"
              />
              <button
                type="button"
                disabled={invite.isPending || !email.trim()}
                className="h-10 shrink-0 rounded-lg bg-[var(--color-primary)] px-4 text-sm font-semibold text-white disabled:opacity-50"
                onClick={() => {
                  setMsg(null);
                  setInviteUrl(null);
                  invite.mutate(email.trim(), {
                    onSuccess: (res) => {
                      setEmail("");
                      const url = `${origin}${res.join_path}`;
                      setInviteUrl(url);
                      setMsg(
                        res.email_sent
                          ? `已邀請 ${res.invited_email}（信已寄出；對方 App 內也有通知）`
                          : `已邀請 ${res.invited_email}（寄信未成功，請複製連結手動傳）`,
                      );
                    },
                    onError: (err) => {
                      const code = errorCode(err);
                      setMsg(ERR_HINT[code] ?? code);
                    },
                  });
                }}
              >
                邀請
              </button>
            </div>
            {msg && (
              <p className="mt-2 text-[12px] text-[var(--color-text-secondary)]">{msg}</p>
            )}
            {inviteUrl && (
              <button
                type="button"
                className="mt-2 text-xs font-semibold text-[var(--color-primary)]"
                onClick={async () => {
                  await navigator.clipboard.writeText(inviteUrl);
                  setMsg("連結已複製");
                }}
              >
                複製邀請連結
              </button>
            )}
          </section>

          <p className="mb-2 text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
            邀請狀態
          </p>
          <div className="mb-4 space-y-2">
            {(invites ?? []).length === 0 ? (
              <p className="text-[12.5px] text-[var(--color-text-secondary)]">尚無邀請紀錄</p>
            ) : (
              (invites ?? []).map((i) => (
                <div
                  key={i.invite_id}
                  className="flex items-center gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-[12.5px]">
                      {i.invited_email ?? "（無 Email）"}
                    </p>
                    <p className="text-[10.5px] text-[var(--color-text-tertiary)]">
                      {STATUS_LABEL[i.status]}
                    </p>
                  </div>
                  {i.status === "pending" && (
                    <button
                      type="button"
                      className="text-[12px] text-[var(--color-text-tertiary)]"
                      onClick={() => {
                        if (window.confirm(`撤銷對 ${i.invited_email} 的邀請？`)) {
                          revoke.mutate(i.invite_id);
                        }
                      }}
                    >
                      撤銷
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </>
      )}

      <p className="mb-2 text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        成員
      </p>
      <div className="space-y-2">
        {data.members.map((m) => (
          <div
            key={m.user_id}
            className="flex items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-[11px] bg-[var(--color-primary-muted)] text-sm font-bold text-[var(--color-primary)]">
              {(m.display_name ?? m.email).slice(0, 1)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{m.display_name ?? m.email}</p>
              <p className="truncate font-mono text-[10.5px] text-[var(--color-text-tertiary)]">
                {m.email}
              </p>
            </div>
            {m.role === "owner" ? (
              <span className="rounded-full bg-[var(--color-primary)] px-2 py-0.5 text-[10px] font-semibold text-white">
                負責人
              </span>
            ) : isOwner ? (
              <button
                type="button"
                className="text-[12px] text-[var(--color-text-tertiary)]"
                onClick={() => {
                  if (window.confirm(`移除 ${m.display_name ?? m.email}？`)) {
                    remove.mutate(m.user_id);
                  }
                }}
              >
                移除
              </button>
            ) : null}
          </div>
        ))}
      </div>

      <div className="mt-6 space-y-2">
        {!isOwner && (
          <button
            type="button"
            className="h-10 w-full rounded-lg bg-[#F5F5F4] text-sm font-medium"
            onClick={() => {
              if (!window.confirm("離開後你將看不到同隊其他人收錄的名片（自己的仍在）。")) return;
              leave.mutate(undefined, {
                onSuccess: () => router.replace("/settings?tab=teams"),
              });
            }}
          >
            離開子團隊
          </button>
        )}
        {isOwner && (
          <button
            type="button"
            className="h-10 w-full rounded-lg bg-[#FEF2F2] text-sm font-semibold text-[#B91C1C]"
            onClick={() => {
              if (!window.confirm("解散後全隊成員改回個人庫；名片不會刪除。確定？")) {
                return;
              }
              dissolve.mutate(undefined, {
                onSuccess: () => router.replace("/settings?tab=teams"),
              });
            }}
          >
            解散子團隊
          </button>
        )}
      </div>
    </div>
  );
}
