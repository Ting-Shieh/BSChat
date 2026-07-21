"use client";

import { useEffect, useState } from "react";
import {
  isAndroid,
  isIOS,
  isLineInAppBrowser,
  isStandalonePwa,
} from "@/shared/lib/browser-env";
import { cn } from "@/shared/lib/cn";

const DISMISS_KEY = "bschat-line-guide-dismiss-until";
const DISMISS_MS = 7 * 24 * 60 * 60 * 1000;

type Props = {
  /** Compact strip on login; full card inside the app shell. */
  variant?: "banner" | "card";
  className?: string;
};

/**
 * LINE in-app browser often clears localStorage → users lose login.
 * Guide them to open in Safari/Chrome once, then Add to Home Screen (PWA).
 */
export function LineBrowserGuide({ variant = "card", className }: Props) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [ios, setIos] = useState(false);
  const [android, setAndroid] = useState(false);

  useEffect(() => {
    if (isStandalonePwa()) return;
    if (!isLineInAppBrowser()) return;
    try {
      const until = Number(localStorage.getItem(DISMISS_KEY) || "0");
      if (until > Date.now()) return;
    } catch {
      /* ignore */
    }
    setIos(isIOS());
    setAndroid(isAndroid());
    setVisible(true);
  }, []);

  if (!visible) return null;

  const appUrl =
    typeof window !== "undefined"
      ? window.location.origin
      : "https://bschat-dogfood.netlify.app";
  const path =
    typeof window !== "undefined"
      ? `${window.location.pathname}${window.location.search}`
      : "/login";
  const fullUrl = `${appUrl}${path.startsWith("/") ? path : `/${path}`}`;

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(appUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  function openInChrome() {
    const hostPath = fullUrl.replace(/^https?:\/\//, "");
    const intent =
      `intent://${hostPath}#Intent;scheme=https;package=com.android.chrome;` +
      `S.browser_fallback_url=${encodeURIComponent(fullUrl)};end`;
    window.location.href = intent;
  }

  function dismiss() {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_MS));
    } catch {
      /* ignore */
    }
    setVisible(false);
  }

  const steps = ios
    ? [
        "右上角「⋯」→ 選擇「用 Safari 開啟」",
        "在 Safari 點分享 →「加入主畫面」",
        "之後從主畫面圖示開啟，登入會較穩定保存",
      ]
    : android
      ? [
          "點下方「用 Chrome 開啟」（或選單 → 用瀏覽器開啟）",
          "在 Chrome 選單 ⋮ → 選「安裝應用程式」（不要只用「加到主畫面」捷徑）",
          "刪掉 LINE 留下的舊捷徑；之後只從新圖示開啟",
        ]
      : [
          "用系統瀏覽器（Safari／Chrome）開啟本站",
          "將網站「加入主畫面」當成 App 使用",
          "之後從主畫面開啟，登入會較穩定保存",
        ];

  if (variant === "banner") {
    return (
      <div
        className={cn(
          "rounded-lg border border-amber-700/40 bg-amber-50 px-3 py-2.5 text-left text-xs text-amber-950",
          className,
        )}
        role="status"
      >
        <p className="font-semibold">偵測到您在 LINE 內開啟</p>
        <p className="mt-1 leading-relaxed text-amber-900/90">
          LINE 內建瀏覽器常會清掉登入狀態。請改用 Safari／Chrome
          開啟，並「加入主畫面」當 App 使用。
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {android && (
            <button
              type="button"
              onClick={openInChrome}
              className="rounded-md bg-amber-900 px-2.5 py-1.5 text-[11px] font-semibold text-white"
            >
              用 Chrome 開啟
            </button>
          )}
          <button
            type="button"
            onClick={copyUrl}
            className="rounded-md bg-amber-900/90 px-2.5 py-1.5 text-[11px] font-semibold text-white"
          >
            {copied ? "已複製網址" : "複製網址"}
          </button>
          <button
            type="button"
            onClick={dismiss}
            className="rounded-md px-2.5 py-1.5 text-[11px] text-amber-900/80 underline"
          >
            稍後再說
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "border-b border-amber-700/30 bg-amber-50 px-4 py-3 text-amber-950",
        className,
      )}
      role="status"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">建議改用主畫面 App 開啟</p>
          <p className="mt-0.5 text-xs leading-relaxed text-amber-900/90">
            您目前在 LINE 內建瀏覽器。這裡常無法長期保存登入；請依下列步驟一次設定。
          </p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="shrink-0 text-xs text-amber-900/70"
          aria-label="關閉提示"
        >
          關閉
        </button>
      </div>
      <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs leading-relaxed text-amber-950">
        {steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <div className="mt-2.5 flex flex-wrap gap-2">
        {android && (
          <button
            type="button"
            onClick={openInChrome}
            className="rounded-lg bg-amber-900 px-3 py-1.5 text-xs font-semibold text-white"
          >
            用 Chrome 開啟
          </button>
        )}
        <button
          type="button"
          onClick={copyUrl}
          className="rounded-lg border border-amber-800/30 bg-white/70 px-3 py-1.5 text-xs font-semibold text-amber-950"
        >
          {copied ? "已複製" : "複製網址"}
        </button>
        <span className="self-center text-[11px] text-amber-900/70">{appUrl}</span>
      </div>
    </div>
  );
}
