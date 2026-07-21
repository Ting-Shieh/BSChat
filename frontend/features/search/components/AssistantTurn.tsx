"use client";

import type { ReactNode } from "react";

/**
 * Shared assistant-turn shell for search conversation.
 * Intent-specific UI fills `children`; follow-ups stay on the page (latest turn).
 */
export function AssistantTurn({
  eyebrow,
  message,
  children,
  layout = "stack",
}: {
  eyebrow?: string | null;
  message?: string | null;
  children?: ReactNode;
  /** bubble = chat-style preview; stack = full-width search hit list */
  layout?: "bubble" | "stack";
}) {
  const hasEyebrow = Boolean(eyebrow?.trim());
  const hasMessage = Boolean(message?.trim());
  const hasBody = children != null && children !== false;

  if (!hasEyebrow && !hasMessage && !hasBody) return null;

  if (layout === "bubble") {
    return (
      <div className="max-w-[92%] rounded-2xl rounded-tl-sm border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3">
        {hasEyebrow && (
          <p className="text-[11px] font-semibold text-[var(--color-ai-text)]">{eyebrow}</p>
        )}
        {hasMessage && (
          <p
            className={`text-[13.5px] leading-relaxed text-[var(--color-text-primary)] ${hasEyebrow ? "mt-1.5" : ""}`}
          >
            {message}
          </p>
        )}
        {hasBody && <div className={hasEyebrow || hasMessage ? "mt-2" : undefined}>{children}</div>}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {hasMessage && (
        <p className="rounded-xl border border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] px-3 py-2.5 text-[13px] leading-relaxed text-[var(--color-ai-text)]">
          {message}
        </p>
      )}
      {children}
    </div>
  );
}
