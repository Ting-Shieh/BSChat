"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  useCreateSubTeamInvite,
  useDissolveSubTeam,
  useLeaveSubTeam,
  useRemoveSubTeamMember,
  useSubTeam,
} from "@/features/subteam/hooks";
import { ApiError } from "@/shared/lib/api-client";

export default function SubTeamDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { data, isLoading, isError } = useSubTeam(id);
  const invite = useCreateSubTeamInvite(id);
  const leave = useLeaveSubTeam(id);
  const dissolve = useDissolveSubTeam(id);
  const remove = useRemoveSubTeamMember(id);
  const [copied, setCopied] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

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

  const isOwner = data.my_role === "owner";
  const origin = typeof window !== "undefined" ? window.location.origin : "";

  async function onInvite() {
    setMsg(null);
    invite.mutate(undefined, {
      onSuccess: async (res) => {
        const url = `${origin}${res.join_path}`;
        try {
          await navigator.clipboard.writeText(url);
          setCopied(true);
          setMsg("邀請連結已複製");
          window.setTimeout(() => setCopied(false), 2000);
        } catch {
          setMsg(url);
        }
      },
      onError: (err) => {
        setMsg(err instanceof ApiError ? err.message : "無法建立邀請");
      },
    });
  }

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
        <div className="mb-3 rounded-xl bg-[var(--color-primary-muted)] px-3 py-2.5 text-[12.5px] text-[var(--color-primary)]">
          你是負責人。邀請同事後，彼此收錄的名片才會在本隊共享。
        </div>
      )}

      <div className="mb-4 flex gap-2">
        <button
          type="button"
          onClick={() => void onInvite()}
          disabled={invite.isPending}
          className="h-10 flex-1 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
        >
          {copied ? "已複製連結" : "複製邀請連結"}
        </button>
      </div>
      {msg && <p className="mb-3 text-[12.5px] text-[var(--color-text-secondary)] break-all">{msg}</p>}

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
              if (
                !window.confirm(
                  "解散後全隊成員改回個人庫；名片不會刪除。確定？",
                )
              ) {
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
