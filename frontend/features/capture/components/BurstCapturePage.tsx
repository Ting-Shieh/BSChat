"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/features/auth/store";
import type { ThumbnailStatus } from "@/shared/types/capture";
import * as captureApi from "../api";
import { useCaptureSession, useCards } from "../hooks";
import { useCaptureStore } from "../store";

function statusBadge(status: ThumbnailStatus) {
  if (status === "ocr_done") return "✅";
  if (status === "ocr_failed" || status === "upload_failed") return "❌";
  if (status === "ocr_processing" || status === "queued") return "⏳";
  if (status === "uploading") return "↑";
  return "·";
}

function isTerminal(status: ThumbnailStatus) {
  return status === "ocr_done" || status === "ocr_failed" || status === "upload_failed";
}

export function BurstCapturePage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sourceLabel, setSourceLabel] = useState("");
  const [sessionReady, setSessionReady] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [duplicateNotice, setDuplicateNotice] = useState<string | null>(null);
  const { sessionId, setSessionId, thumbnails, addThumbnail, updateThumbnail, clear } =
    useCaptureStore();
  const { data: session } = useCaptureSession(sessionId);
  const { data: cardsData } = useCards(sessionId ? { session_id: sessionId } : {});

  useEffect(() => {
    if (!token || sessionId) {
      if (sessionId) setSessionReady(true);
      return;
    }
    let cancelled = false;
    captureApi
      .createSession(token, { source_type: "event" })
      .then((s) => {
        if (!cancelled) {
          setSessionId(s.id);
          setSessionReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) setInitError("無法建立收錄 session");
      });
    return () => {
      cancelled = true;
    };
  }, [token, sessionId, setSessionId]);

  useEffect(() => {
    const items = cardsData?.items ?? [];
    if (!items.length) return;
    for (const thumb of thumbnails) {
      if (!thumb.cardId) continue;
      const card = items.find((c) => c.id === thumb.cardId);
      if (card && card.status !== thumb.status) {
        updateThumbnail(thumb.localUrl, { status: card.status as ThumbnailStatus });
      }
    }
  }, [cardsData, thumbnails, updateThumbnail]);

  const uploadFile = useCallback(
    async (file: File, localUrl: string) => {
      if (!token || !sessionId) {
        updateThumbnail(localUrl, { status: "upload_failed" });
        return;
      }
      const key = `cap-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      try {
        const { default: imageCompression } = await import("browser-image-compression");
        const compressed = await imageCompression(file, { maxWidthOrHeight: 2048, useWebWorker: true });
        const res = await captureApi.uploadCard(token, sessionId, compressed, key);
        updateThumbnail(localUrl, { status: "queued", cardId: res.raw_card_id });
        if (res.duplicate_warning?.message) {
          setDuplicateNotice(res.duplicate_warning.message);
          window.setTimeout(() => setDuplicateNotice(null), 5000);
        }
      } catch {
        updateThumbnail(localUrl, { status: "upload_failed" });
      }
    },
    [token, sessionId, updateThumbnail],
  );

  const handleCapture = async (file: File) => {
    if (!sessionReady || !sessionId) return;
    const localUrl = URL.createObjectURL(file);
    addThumbnail({ id: localUrl, localUrl, status: "uploading" });
    await uploadFile(file, localUrl);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleCapture(file);
    e.target.value = "";
  };

  const finishSession = async () => {
    if (token && sessionId) {
      await captureApi.closeSession(token, sessionId, sourceLabel || undefined);
    }
    clear();
    router.push(`/capture/session/${sessionId}`);
  };

  const doneCount = session?.confirmed_count ?? 0;
  const pendingCount = session?.pending_count ?? 0;
  const processingCount = thumbnails.filter((t) => !isTerminal(t.status)).length;

  return (
    <div className="theme-camera flex min-h-dvh flex-1 flex-col bg-black text-[var(--color-text-primary)]">
      <header className="flex items-center justify-between px-4 py-3 text-white">
        <Link href="/capture" className="text-sm text-zinc-400">
          返回
        </Link>
        <span className="text-sm">連拍收錄</span>
        <button type="button" onClick={() => void finishSession()} className="text-sm text-amber-400">
          完成
        </button>
      </header>

      {duplicateNotice && (
        <div className="mx-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          {duplicateNotice}（已照常收錄）
        </div>
      )}

      <div className="px-4 pb-2">
        <input
          type="text"
          placeholder="場合標籤（選填，如 Computex 2026）"
          value={sourceLabel}
          onChange={(e) => setSourceLabel(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white"
        />
      </div>

      <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center bg-zinc-900">
        <p className="mb-6 text-center text-sm text-zinc-400">
          {!sessionReady
            ? "正在準備收錄…"
            : initError
              ? "無法連上伺服器"
              : "點擊下方快門拍攝名片"}
          <br />
          {sessionReady && !initError && "可使用相機或相簿"}
        </p>
        {initError && <p className="mb-4 text-sm text-red-400">{initError}</p>}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={onFileChange}
        />
        <button
          type="button"
          disabled={!sessionReady || !!initError}
          onClick={() => fileInputRef.current?.click()}
          className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-amber-600 ring-4 ring-amber-600/30 disabled:opacity-40"
          aria-label="快門"
        />
        {processingCount > 0 && (
          <p className="mt-4 text-center text-xs text-zinc-500">
            AI 辨識中…（若過久請檢查後端 Gemini key）
          </p>
        )}
      </div>

      {thumbnails.length > 0 && (
        <div className="border-t border-zinc-800 bg-zinc-950 p-3">
          <div className="mb-2 flex gap-3 overflow-x-auto">
            {thumbnails.map((t) => (
              <div key={t.id} className="relative shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={t.localUrl}
                  alt=""
                  className={`h-16 w-12 rounded object-cover ${t.status === "ocr_done" ? "ring-2 ring-emerald-500" : ""}`}
                />
                {!isTerminal(t.status) && (
                  <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900 text-xs">
                    {statusBadge(t.status)}
                  </span>
                )}
                {t.status === "ocr_done" && (
                  <span className="absolute -right-1 -top-1 text-xs">✅</span>
                )}
                {(t.status === "ocr_failed" || t.status === "upload_failed") && (
                  <span className="absolute -right-1 -top-1 text-xs">❌</span>
                )}
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-zinc-500">
            已拍 {thumbnails.length} 張
            {processingCount > 0 ? ` · 處理中 ${processingCount}` : ""}
            {doneCount + pendingCount > 0 ? ` · 完成 ${doneCount + pendingCount}` : ""}
          </p>
        </div>
      )}
    </div>
  );
}
