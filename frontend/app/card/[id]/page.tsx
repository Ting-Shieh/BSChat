"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchPublicCard, type PublicCard } from "@/features/org/api";
import { ApiError } from "@/shared/lib/api-client";

export default function PublicCardPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [card, setCard] = useState<PublicCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    fetchPublicCard(id)
      .then((data) => {
        if (!cancelled) setCard(data);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("找不到這張名片，或尚未開放 AI 推薦。");
        } else {
          setError("載入失敗，請稍後再試。");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const keywords = [
    ...(card?.responsibility_keywords ?? []),
    ...(card?.product_keywords ?? []),
  ];

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-5 py-10">
      <p className="text-center text-[11px] font-semibold tracking-wide text-[var(--color-text-tertiary)]">
        BSChat · 電子名片
      </p>

      {error && (
        <p className="mt-8 text-center text-sm text-[var(--color-text-secondary)]">{error}</p>
      )}

      {!error && !card && (
        <p className="mt-8 text-center text-sm text-[var(--color-text-tertiary)]">載入中…</p>
      )}

      {card && (
        <article className="mt-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
          <div className="flex items-start gap-3">
            {card.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={card.avatar_url}
                alt=""
                className="h-14 w-14 rounded-xl object-cover"
              />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-[var(--color-primary-muted)] text-lg font-bold text-[var(--color-primary)]">
                {card.display_name.slice(0, 1)}
              </div>
            )}
            <div className="min-w-0">
              <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
                {card.display_name}
              </h1>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {card.title ?? "—"} · {card.company_name}
              </p>
              <p className="mt-0.5 text-[11px] text-[var(--color-text-tertiary)]">{card.org_name}</p>
            </div>
          </div>

          {card.one_line_blurb && (
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-primary)]">
              {card.one_line_blurb}
            </p>
          )}

          {keywords.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {keywords.map((k) => (
                <span
                  key={k}
                  className="rounded-md bg-[#F5F5F4] px-2 py-0.5 text-[11px] text-[var(--color-text-secondary)]"
                >
                  {k}
                </span>
              ))}
            </div>
          )}

          <a
            href={card.external_card_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 block w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-center text-sm font-semibold text-white"
          >
            開啟對外連結
          </a>

          <button
            type="button"
            className="mt-3 w-full py-2 text-xs text-[var(--color-text-secondary)]"
            onClick={() => {
              void navigator.clipboard?.writeText(window.location.href).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              });
            }}
          >
            {copied ? "已複製本頁連結" : "複製本頁連結"}
          </button>

          <p className="mt-4 text-center text-[10px] leading-relaxed text-[var(--color-text-tertiary)]">
            此頁不含電話與 Email；聯絡請走對外連結。
          </p>
        </article>
      )}
    </main>
  );
}
