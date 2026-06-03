"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import type { IDetectedBarcode } from "@yudiel/react-qr-scanner";
import { CopyToast } from "@/features/actions";
import { useAuthStore } from "@/features/auth/store";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";
import { cn } from "@/shared/lib/cn";
import type { ScanPhase } from "./QrScannerPanel";
import * as captureApi from "../api";

const QrScannerPanel = dynamic(
  () => import("./QrScannerPanel").then((m) => m.QrScannerPanel),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-sm text-white/80">載入掃描器…</div>
    ),
  },
);

function scanStatusText(phase: ScanPhase, scanning: boolean): string {
  if (phase === "importing") return "讀取成功，收錄中…";
  if (phase === "detected") return "已偵測 QR，鎖定中…";
  if (scanning) return "將 QR code 對準藍框";
  return "點下方按鈕開啟相機";
}

export function ScanQrPage() {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [scanning, setScanning] = useState(false);
  const [scanPhase, setScanPhase] = useState<ScanPhase>("idle");
  const [manualPayload, setManualPayload] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submitPayload = useCallback(
    async (payload: string) => {
      if (!token || !payload.trim() || loading) return;
      setLoading(true);
      setScanPhase("importing");
      setError(null);
      setMessage(null);
      try {
        const resp = await captureApi.importQr(token, payload.trim());
        setMessage(resp.message);
        setScanning(false);
        await queryClient.invalidateQueries({ queryKey: ["contacts"] });
        await queryClient.invalidateQueries({ queryKey: ["cards"] });
        await queryClient.invalidateQueries({ queryKey: ["pending-count"] });
        setTimeout(() => router.push("/contacts"), 1200);
      } catch (err) {
        const detail = (err as { message?: string }).message ?? "無法解析此 QR";
        setError(detail);
        setScanPhase("idle");
      } finally {
        setLoading(false);
      }
    },
    [token, loading, router, queryClient],
  );

  const handleDetect = useCallback(
    async (code: IDetectedBarcode) => {
      setScanPhase("detected");
      await new Promise((r) => setTimeout(r, 350));
      await submitPayload(code.rawValue);
    },
    [submitPayload],
  );

  return (
    <main className="flex flex-col gap-4 p-4">
      <Link href="/capture" className="text-sm text-[var(--color-primary)]">
        ← 收錄
      </Link>

      <div>
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">掃 QR 收電子名片</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          對準對方的電子名片 QR code，掃描後直接收進名片庫。
        </p>
      </div>

      <div className="relative aspect-[3/4] max-h-80 overflow-hidden rounded-xl border border-[var(--color-border)] bg-black">
        {scanning ? (
          <>
            <QrScannerPanel
              phase={scanPhase}
              paused={loading || scanPhase === "importing"}
              onDetect={(code) => void handleDetect(code)}
              onError={(msg) => {
                setError(msg);
                setScanning(false);
                setScanPhase("idle");
              }}
            />
            <div
              className={cn(
                "absolute bottom-3 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium text-white shadow-lg",
                scanPhase === "detected" || scanPhase === "importing"
                  ? "bg-emerald-600/90"
                  : "bg-black/70",
              )}
              aria-live="polite"
            >
              {scanStatusText(scanPhase, scanning)}
            </div>
          </>
        ) : (
          <div className="flex h-full min-h-64 items-center justify-center bg-[var(--color-surface)]/90">
            <button
              type="button"
              onClick={() => {
                setError(null);
                setScanPhase("idle");
                setScanning(true);
              }}
              className="rounded-xl bg-[var(--color-accent)] px-4 py-3 text-sm font-semibold text-white"
            >
              開啟相機掃描
            </button>
          </div>
        )}
      </div>

      <p className="text-xs text-[var(--color-text-tertiary)]">
        若相機無法開啟，請改貼連結或下方手動貼上 QR 內容。
      </p>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-[var(--color-text-secondary)]">或手動貼上 QR 內容</label>
        <textarea
          value={manualPayload}
          onChange={(e) => setManualPayload(e.target.value)}
          placeholder="BEGIN:VCARD... 或 https://..."
          rows={3}
          className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
        />
        <button
          type="button"
          disabled={loading || !manualPayload.trim()}
          onClick={() => void submitPayload(manualPayload)}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "解析中…" : "提交 QR 內容"}
        </button>
      </div>

      {error && (
        <p className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 px-3 py-2 text-sm text-[var(--color-error)]">
          {error}
        </p>
      )}

      <Link href="/capture/import-url" className="text-center text-sm text-[var(--color-primary)]">
        改貼連結收電子名片
      </Link>
      <PrivacyStrip />
      <CopyToast message={message} />
    </main>
  );
}
