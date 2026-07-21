"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useCreateSubTeam, useSubTeams } from "../hooks";
import { ApiError } from "@/shared/lib/api-client";

export function SubTeamSettingsPanel() {
  const router = useRouter();
  const { data: teams, isLoading, isError, error } = useSubTeams(true);
  const create = useCreateSubTeam();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  function onCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    create.mutate(
      { name: name.trim(), description: description.trim() || undefined },
      {
        onSuccess: (team) => {
          setOpen(false);
          setName("");
          setDescription("");
          router.push(`/teams/${team.id}`);
        },
        onError: (err) => {
          setFormError(
            err instanceof ApiError ? err.message : "建立失敗",
          );
        },
      },
    );
  }

  if (isLoading) {
    return <p className="text-sm text-[var(--color-text-secondary)]">載入子團隊…</p>;
  }

  if (isError) {
    const msg =
      error instanceof ApiError && error.status === 403
        ? "需要企業成員身份才能使用子團隊。"
        : "無法載入子團隊";
    return <p className="text-sm text-[var(--color-text-secondary)]">{msg}</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-[12.5px] leading-relaxed text-[var(--color-text-secondary)]">
        名片只與<strong className="text-[var(--color-text-primary)]">同隊</strong>
        成員共享。企業成員可自助建隊；主 Admin 可解散任何隊。
      </p>

      {(teams ?? []).length === 0 && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-4 text-center text-[12.5px] text-[var(--color-text-secondary)]">
          尚未加入子團隊 · 目前只有自己看得到名片
        </div>
      )}

      {(teams ?? []).map((t) => (
        <div
          key={t.id}
          className="flex items-center justify-between gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3"
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--color-text-primary)]">
              {t.name}
            </p>
            <p className="mt-0.5 text-[11.5px] text-[var(--color-text-tertiary)]">
              {t.member_count} 人
              {t.role === "owner" ? " · 你是負責人" : ""}
            </p>
          </div>
          <Link
            href={`/teams/${t.id}`}
            className="shrink-0 rounded-lg border border-[var(--color-primary)] px-2.5 py-1.5 text-xs font-semibold text-[var(--color-primary)]"
          >
            進入
          </Link>
        </div>
      ))}

      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="h-11 w-full rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white"
        >
          ＋ 建立子團隊
        </button>
      ) : (
        <form
          onSubmit={onCreate}
          className="space-y-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5"
        >
          <p className="text-sm font-semibold">建立子團隊</p>
          <div>
            <label className="mb-1 block text-[12.5px] font-medium">隊名</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-primary)]"
              placeholder="例如：業務一組"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12.5px] font-medium">說明（選填）</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-primary)]"
              rows={2}
            />
          </div>
          {formError && <p className="text-[12.5px] text-red-600">{formError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="h-10 flex-1 rounded-lg bg-[#F5F5F4] text-sm font-medium"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="h-10 flex-[1.2] rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
            >
              {create.isPending ? "建立中…" : "建立"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
