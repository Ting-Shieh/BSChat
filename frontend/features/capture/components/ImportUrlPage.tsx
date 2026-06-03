"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { CopyToast } from "@/features/actions";
import { useAuthStore } from "@/features/auth/store";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import * as captureApi from "../api";

export function ImportUrlPage() {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handlePaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (text.trim()) setUrl(text.trim());
    } catch {
      setError("無法讀取剪貼簿，請手動貼上連結");
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token || !url.trim()) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const resp = await captureApi.importUrl(token, url.trim(), { force: true });
      setMessage(resp.message);
      await queryClient.invalidateQueries({ queryKey: ["contacts"] });
      await queryClient.invalidateQueries({ queryKey: ["cards"] });
      await queryClient.invalidateQueries({ queryKey: ["pending-count"] });
      setTimeout(() => router.push("/contacts"), 1200);
    } catch (err) {
      const detail = (err as { message?: string }).message ?? "無法解析此連結";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col gap-4 p-4">
      <Link href="/capture" className="text-sm text-[var(--color-primary)]">
        ← 收錄
      </Link>

      <div>
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">貼連結收電子名片</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          從 LINE 或 Email 複製對方的電子名片連結，貼到這裡即可收進名片庫。
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-3">
        <textarea
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://... 或 vCard 文字"
          rows={4}
          className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void handlePaste()}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
          >
            📋 貼上剪貼簿
          </button>
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="flex-1 rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "解析中…" : "收進名片庫"}
          </button>
        </div>
      </form>

      {error && (
        <p className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 px-3 py-2 text-sm text-[var(--color-error)]">
          {error}
        </p>
      )}

      <p className="text-xs text-[var(--color-text-tertiary)]">
        支援 vCard（.vcf）連結與常見聯絡資訊網頁。若無法解析，請改用連拍或手動新增。
      </p>
      <PrivacyStrip />
      <CopyToast message={message} />
    </main>
  );
}
