"use client";

import { useState } from "react";
import Link from "next/link";
import { useMe } from "@/features/auth/hooks";
import {
  useMyEnterpriseApplications,
  useSubmitEnterpriseApplication,
} from "@/features/enterprise/hooks";

export default function EnterpriseApplyPage() {
  const { data: me } = useMe();
  const { data: apps } = useMyEnterpriseApplications();
  const submit = useSubmitEnterpriseApplication();
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [slug, setSlug] = useState("");
  const [seats, setSeats] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const pending = apps?.find((a) => a.status === "pending");

  if (!me) {
    return (
      <div className="mx-auto max-w-md px-4 py-10 text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  if (done || pending) {
    return (
      <div className="mx-auto max-w-md px-4 py-10">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">企業申請</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          已送出，審核中。核准後你會成為該企業的主 Admin。
        </p>
        <Link href="/settings" className="mt-6 inline-block text-sm text-[var(--color-primary)]">
          回「我的」
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">申請企業版</h1>
      <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
        送出後由平台核准開通；開通後你可邀請業務成員並管理電子名片。
      </p>

      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          submit.mutate(
            {
              company_name: company.trim(),
              contact_email: (email.trim() || me.email).toLowerCase(),
              slug_requested: slug.trim() || undefined,
              estimated_seats: seats ? Number(seats) : undefined,
              note: note.trim() || undefined,
            },
            {
              onSuccess: () => setDone(true),
              onError: (err) => setError(err instanceof Error ? err.message : "送出失敗"),
            },
          );
        }}
      >
        <input
          required
          className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          placeholder="公司名稱"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          placeholder={`聯絡 Email（預設 ${me.email}）`}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          placeholder="代號（選填，如 acme）"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          placeholder="預估人數（選填）"
          inputMode="numeric"
          value={seats}
          onChange={(e) => setSeats(e.target.value)}
        />
        <textarea
          className="w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
          placeholder="備註（選填）"
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submit.isPending || !company.trim()}
          className="w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {submit.isPending ? "送出中…" : "送出申請"}
        </button>
      </form>
    </div>
  );
}
