"use client";

import { useEffect, useState } from "react";
import {
  isAndroid,
  isLineInAppBrowser,
  isStandalonePwa,
} from "@/shared/lib/browser-env";
import { cn } from "@/shared/lib/cn";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

type Props = {
  className?: string;
  /** Compact for settings; banner for shell. */
  variant?: "card" | "settings";
};

/**
 * Android Chrome: real PWA install (correct icon) needs Chrome "Install app",
 * not LINE's "Add to Home" bookmark shortcut.
 */
export function PwaInstallHint({ className, variant = "card" }: Props) {
  const [show, setShow] = useState(false);
  const [inLine, setInLine] = useState(false);
  const [android, setAndroid] = useState(false);
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isStandalonePwa()) return;
    const line = isLineInAppBrowser();
    const and = isAndroid();
    // LINE 內由 LineBrowserGuide 處理；這裡專責 Chrome / 已可安裝的 Android。
    if (line) return;
    if (!and) {
      // still listen for BIP on desktop Chrome etc.
    }
    setInLine(false);
    setAndroid(and);

    function onBip(e: Event) {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setShow(true);
    }
    window.addEventListener("beforeinstallprompt", onBip);

    if (and) setShow(true);

    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  if (!show) return null;

  const origin =
    typeof window !== "undefined"
      ? window.location.origin
      : "https://bschat-dogfood.netlify.app";
  const path =
    typeof window !== "undefined"
      ? `${window.location.pathname}${window.location.search}`
      : "/";
  const fullUrl = `${origin}${path === "/" ? "/login" : path}`;

  async function install() {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    setShow(false);
  }

  function openInChrome() {
    // Prefer Chrome Intent so LINE hands off to a real browser (PWA-capable).
    const hostPath = fullUrl.replace(/^https?:\/\//, "");
    const intent =
      `intent://${hostPath}#Intent;scheme=https;package=com.android.chrome;` +
      `S.browser_fallback_url=${encodeURIComponent(fullUrl)};end`;
    window.location.href = intent;
  }

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(origin);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  const body = inLine ? (
    <>
      <p className="text-sm font-semibold text-[var(--color-text-primary)]">
        Android：請用 Chrome 安裝
      </p>
      <p className="mt-1 text-xs leading-relaxed text-[var(--color-text-secondary)]">
        在 LINE 裡「加到主畫面」通常只是捷徑，圖示／登入都容易異常。請改用
        Chrome 開啟後選「安裝應用程式」。
      </p>
    </>
  ) : (
    <>
      <p className="text-sm font-semibold text-[var(--color-text-primary)]">
        安裝 BSChat 到主畫面
      </p>
      <p className="mt-1 text-xs leading-relaxed text-[var(--color-text-secondary)]">
        安裝後從主畫面開啟，登入較穩定，也會顯示正確 App 圖示。
      </p>
    </>
  );

  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5",
        variant === "card" && "mx-0",
        className,
      )}
      role="status"
    >
      {body}
      <div className="mt-2.5 flex flex-wrap gap-2">
        {inLine && android && (
          <button
            type="button"
            onClick={openInChrome}
            className="rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-semibold text-white"
          >
            用 Chrome 開啟
          </button>
        )}
        {deferred && (
          <button
            type="button"
            onClick={() => void install()}
            className="rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-semibold text-white"
          >
            安裝應用程式
          </button>
        )}
        {!deferred && !inLine && android && (
          <p className="w-full text-[11px] text-[var(--color-text-tertiary)]">
            Chrome 選單 ⋮ →「安裝應用程式」或「加到主畫面」
          </p>
        )}
        <button
          type="button"
          onClick={() => void copyUrl()}
          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)]"
        >
          {copied ? "已複製網址" : "複製網址"}
        </button>
      </div>
    </div>
  );
}
