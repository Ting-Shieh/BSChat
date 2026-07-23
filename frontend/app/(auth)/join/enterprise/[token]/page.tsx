"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { previewEnterpriseInvite } from "@/features/enterprise/api";
import type { EnterpriseInvitePreview } from "@/features/enterprise/api";
import { useAcceptEnterpriseInvite } from "@/features/enterprise/hooks";
import { useMe } from "@/features/auth/hooks";
import { useAuthStore } from "@/features/auth/store";
import { formatApiError } from "@/shared/lib/api-client";

function JoinEnterpriseBody() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const router = useRouter();
  const bschatToken = useAuthStore((s) => s.token);
  const { data: me, refetch: refetchMe } = useMe();
  const accept = useAcceptEnterpriseInvite();
  const [preview, setPreview] = useState<EnterpriseInvitePreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void previewEnterpriseInvite(token)
      .then(setPreview)
      .catch((e) => {
        const msg = formatApiError(e, "邀請無效或已過期");
        // 連結已用過且本人已是企業成員 → 直接進名片庫
        const alreadyInOrg = (me?.org_memberships || []).some((o) => o.is_enterprise);
        if (msg.includes("已使用") && bschatToken && alreadyInOrg) {
          router.replace("/contacts");
          return;
        }
        setError(msg);
      });
  }, [token, me, bschatToken, router]);

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
          返回名片庫
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
        <p className="text-xs text-[var(--color-text-tertiary)]">企業成員邀請</p>
        <p className="mt-1 text-lg font-semibold text-[var(--color-text-primary)]">
          加入 {preview.org_name}
        </p>
        {preview.invited_email && (
          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
            僅限 {preview.invited_email}
          </p>
        )}
      </div>

      {bschatToken ? (
        <p className="text-sm text-[var(--color-text-secondary)]">正在加入企業…</p>
      ) : (
        <div className="flex flex-col gap-2">
          <Link
            href={`/register?invite_enterprise=${q}`}
            className="rounded-lg bg-[var(--color-primary)] px-4 py-2.5 text-center text-sm font-semibold text-white"
          >
            註冊並加入
          </Link>
          <Link
            href={`/login?invite_enterprise=${q}`}
            className="rounded-lg border border-[var(--color-border)] bg-white px-4 py-2.5 text-center text-sm font-semibold text-[var(--color-text-primary)]"
          >
            登入並加入
          </Link>
        </div>
      )}
    </div>
  );
}

export default function JoinEnterprisePage() {
  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">加入企業租戶</p>
      </div>
      <Suspense fallback={<p className="text-sm text-[var(--color-text-secondary)]">載入中…</p>}>
        <JoinEnterpriseBody />
      </Suspense>
    </main>
  );
}
