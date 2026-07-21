"use client";

import { useEffect, useState } from "react";
import { useMyPublicIdentities, useUpdateMyPublicIdentity } from "@/features/enterprise/hooks";

function normalizePublicUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function stateLabel(aiState: string): string {
  if (aiState === "on") return "AI 推薦：已曝光";
  if (aiState === "pending_url") return "AI 預設開 · 待補我的名片";
  if (aiState === "off") return "AI 推薦：關";
  return "尚未建立公開身份";
}

export function MyPublicIdentityPanel() {
  const { data: identities, isLoading } = useMyPublicIdentities();
  const update = useUpdateMyPublicIdentity();
  const [drafts, setDrafts] = useState<Record<string, { url: string; title: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [savedOrgId, setSavedOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (!identities) return;
    const next: Record<string, { url: string; title: string }> = {};
    for (const id of identities) {
      next[id.org_id] = {
        url: id.external_card_url ?? "",
        title: id.title ?? "",
      };
    }
    setDrafts(next);
  }, [identities]);

  if (isLoading) {
    return <p className="text-xs text-[var(--color-text-secondary)]">載入公開身份…</p>;
  }
  if (!identities?.length) return null;

  return (
    <section className="space-y-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5">
      <div>
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">我的名片</h2>
        <p className="mt-1 text-[11px] leading-relaxed text-[var(--color-text-secondary)]">
          放你自己的名片頁（LinkedIn 個人頁、公司個人頁、既有名片商頁均可）。有名片連結後才會被 AI
          推薦；邀請中不會曝光。
        </p>
      </div>
      {identities.map((id) => {
        const draft = drafts[id.org_id] ?? { url: "", title: "" };
        return (
          <div
            key={id.org_id}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-3"
          >
            <p className="text-sm font-medium text-[var(--color-text-primary)]">{id.org_name}</p>
            <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">
              {stateLabel(id.ai_state)}
            </p>
            <label className="mt-2 block text-xs">
              <span className="text-[var(--color-text-secondary)]">職稱（選填）</span>
              <input
                value={draft.title}
                onChange={(e) =>
                  setDrafts((prev) => ({
                    ...prev,
                    [id.org_id]: { ...draft, title: e.target.value },
                  }))
                }
                className="mt-1 w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-2 block text-xs">
              <span className="text-[var(--color-text-secondary)]">我的名片連結</span>
              <input
                value={draft.url}
                onChange={(e) =>
                  setDrafts((prev) => ({
                    ...prev,
                    [id.org_id]: { ...draft, url: e.target.value },
                  }))
                }
                placeholder="https://www.linkedin.com/in/… 或你的名片頁"
                className="mt-1 w-full rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
              />
            </label>
            <button
              type="button"
              disabled={update.isPending || !draft.url.trim()}
              className="mt-2 w-full rounded-lg bg-[var(--color-primary)] py-2 text-sm font-medium text-white disabled:opacity-50"
              onClick={() => {
                const url = normalizePublicUrl(draft.url);
                if (!url) {
                  setError("請填我的名片連結");
                  return;
                }
                setError(null);
                update.mutate(
                  {
                    orgId: id.org_id,
                    body: {
                      external_card_url: url,
                      title: draft.title.trim() || null,
                    },
                  },
                  {
                    onSuccess: () => {
                      setSavedOrgId(id.org_id);
                      window.setTimeout(() => setSavedOrgId(null), 2000);
                    },
                    onError: (e) => setError(e instanceof Error ? e.message : "儲存失敗"),
                  },
                );
              }}
            >
              {savedOrgId === id.org_id ? "已儲存" : "儲存名片並開啟 AI"}
            </button>
          </div>
        );
      })}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </section>
  );
}
