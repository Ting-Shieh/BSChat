"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { previewInvite } from "@/features/auth/api";
import type { InvitePreview } from "@/shared/types/auth";
import { useAcceptInvite, useMe } from "@/features/auth/hooks";
import { useAuthStore } from "@/features/auth/store";
import { formatApiError } from "@/shared/lib/api-client";

function JoinBody() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const router = useRouter();
  const bschatToken = useAuthStore((s) => s.token);
  const { data: me, refetch: refetchMe } = useMe();
  const accept = useAcceptInvite();
  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void previewInvite(token)
      .then(setPreview)
      .catch((e) => {
        setError(formatApiError(e, "邀請無效或已過期"));
      });
  }, [token]);

  useEffect(() => {
    if (!bschatToken || !token || !preview || accept.isPending || accept.isSuccess) return;
    const already = (me?.org_memberships || []).some((o) => o.org_id === preview.org_id);
    if (already) {
      router.replace("/contacts");
      return;
    }
    accept.mutate(token, {
      onSuccess: async () => {
        await refetchMe();
        router.replace("/contacts");
        router.refresh();
      },
      onError: (e) => setError(formatApiError(e, "加入失敗")),
    });
  }, [bschatToken, token, preview, me, accept, router, refetchMe]);

  if (error) {
    return (
      <div className="flex w-full max-w-sm flex-col gap-3">
        <p className="text-sm leading-relaxed text-red-600">{error}</p>
        <Link
          href="/contacts"
          className="rounded-lg border border-[var(--color-border)] bg-white px-4 py-2.5 text-center text-sm font-semibold"
        >
          返回
        </Link>
      </div>
    );
  }

  if (!preview) {
    return <p className="text-sm text-[var(--color-text-secondary)]">檢查邀請連結…</p>;
  }

  const q = encodeURIComponent(token);

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <p className="text-xs text-[var(--color-text-tertiary)]">團隊邀請</p>
        <p className="mt-1 text-lg font-semibold">{preview.org_name}</p>
      </div>
      {bschatToken ? (
        <p className="text-sm text-[var(--color-text-secondary)]">正在加入…</p>
      ) : (
        <div className="flex flex-col gap-2">
          <Link
            href={`/register?invite_token=${q}`}
            className="rounded-lg bg-[var(--color-primary)] px-4 py-2.5 text-center text-sm font-semibold text-white"
          >
            註冊並加入
          </Link>
          <Link
            href={`/login?invite_token=${q}`}
            className="rounded-lg border border-[var(--color-border)] bg-white px-4 py-2.5 text-center text-sm font-semibold"
          >
            登入並加入
          </Link>
        </div>
      )}
    </div>
  );
}

export default function JoinPage() {
  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">加入團隊</p>
      </div>
      <Suspense fallback={<p className="text-sm text-[var(--color-text-secondary)]">載入中…</p>}>
        <JoinBody />
      </Suspense>
    </main>
  );
}
