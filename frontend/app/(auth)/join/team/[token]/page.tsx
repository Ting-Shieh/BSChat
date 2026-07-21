"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { previewSubTeamInvite } from "@/features/subteam/api";
import type { SubTeamInvitePreview } from "@/features/subteam/api";
import { useAcceptSubTeamInvite } from "@/features/subteam/hooks";
import { useAuthStore } from "@/features/auth/store";
import { formatApiError } from "@/shared/lib/api-client";

export default function JoinSubTeamPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const router = useRouter();
  const authToken = useAuthStore((s) => s.token);
  const accept = useAcceptSubTeamInvite();
  const [preview, setPreview] = useState<SubTeamInvitePreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void previewSubTeamInvite(token)
      .then((p) => {
        if (!cancelled) setPreview(p);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(formatApiError(err, "邀請無效或已過期"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function onAccept() {
    if (!authToken) {
      router.push(`/login?next=${encodeURIComponent(`/join/team/${token}`)}`);
      return;
    }
    accept.mutate(token, {
      onSuccess: () => {
        router.replace("/settings?tab=teams");
        router.refresh();
      },
      onError: (err) => {
        setError(formatApiError(err, "加入失敗"));
      },
    });
  }

  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="w-full max-w-sm text-center">
        <p className="text-sm font-semibold tracking-wide text-[var(--color-primary)]">BSChat</p>
        <h1 className="mt-3 text-2xl font-semibold">加入子團隊</h1>
        {preview && (
          <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-secondary)]">
            <span className="font-semibold text-[var(--color-text-primary)]">{preview.org_name}</span>
            <br />
            {preview.sub_team_name}
          </p>
        )}
      </div>

      <div className="w-full max-w-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-left text-[12.5px] leading-relaxed text-[var(--color-text-secondary)]">
        加入後，你與同隊成員的名片庫互相可見。這不是企業開通邀請；也不會把名片公開給 AI 推薦。
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex w-full max-w-sm flex-col gap-2">
        <button
          type="button"
          disabled={!preview || accept.isPending}
          onClick={onAccept}
          className="h-11 rounded-lg bg-[var(--color-primary)] text-sm font-semibold text-white disabled:opacity-50"
        >
          {accept.isPending ? "加入中…" : "接受並加入"}
        </button>
        <Link
          href="/settings"
          className="h-11 rounded-lg bg-[#F5F5F4] text-center text-sm font-medium leading-[44px] text-[var(--color-text-secondary)]"
        >
          取消
        </Link>
      </div>
    </main>
  );
}
