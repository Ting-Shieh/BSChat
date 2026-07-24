"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/shared/lib/cn";

type CameraState = "starting" | "live" | "denied" | "unavailable";

/**
 * Live rear-camera preview (getUserMedia). Shutter freezes a JPEG frame.
 * Falls back to caller when permission / device is unavailable.
 */
export function CameraViewfinder({
  active,
  disabled,
  onCapture,
  onNeedFallback,
}: {
  active: boolean;
  disabled?: boolean;
  onCapture: (file: File) => void;
  onNeedFallback: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("starting");
  const [capturing, setCapturing] = useState(false);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => {
    if (!active) {
      stopStream();
      return;
    }
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setState("unavailable");
      onNeedFallback();
      return;
    }

    let cancelled = false;
    setState("starting");

    void (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => undefined);
        }
        setState("live");
      } catch {
        if (cancelled) return;
        setState("denied");
        onNeedFallback();
      }
    })();

    return () => {
      cancelled = true;
      stopStream();
    };
  }, [active, onNeedFallback, stopStream]);

  const takePhoto = async () => {
    const video = videoRef.current;
    if (!video || state !== "live" || disabled || capturing) return;
    if (!video.videoWidth || !video.videoHeight) return;

    setCapturing(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0);
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.92),
      );
      if (!blob) return;
      const file = new File([blob], `card-${Date.now()}.jpg`, { type: "image/jpeg" });
      onCapture(file);
    } finally {
      setCapturing(false);
    }
  };

  return (
    <div className="relative flex min-h-0 w-full flex-1 flex-col">
      <div className="relative min-h-0 flex-1 overflow-hidden bg-black">
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          className={cn(
            "absolute inset-0 h-full w-full object-cover",
            state !== "live" && "invisible",
          )}
        />
        {state === "starting" && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-zinc-400">
            正在開啟相機…
          </p>
        )}
        {(state === "denied" || state === "unavailable") && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <p className="text-sm text-zinc-300">
              {state === "denied" ? "無法取得相機權限" : "此裝置不支援即時相機"}
            </p>
            <p className="text-xs text-zinc-500">請改用下方按鈕開啟系統相機或相簿</p>
          </div>
        )}
        {state === "live" && (
          <div className="pointer-events-none absolute inset-x-0 top-1/2 flex -translate-y-1/2 justify-center">
            <div className="h-40 w-[85%] max-w-sm rounded-xl border border-white/50 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]" />
          </div>
        )}
      </div>

      <div className="flex flex-col items-center gap-3 bg-zinc-950 px-4 pb-6 pt-4">
        <p className="text-center text-xs text-zinc-400">
          {state === "live"
            ? "對準名片，點快門連續拍 — 不用填欄位"
            : "點下方按鈕開啟相機或相簿"}
        </p>
        {state === "live" ? (
          <button
            type="button"
            disabled={disabled || capturing}
            onClick={() => void takePhoto()}
            className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-[var(--color-accent)] ring-4 ring-white disabled:opacity-40"
            aria-label="快門拍照"
          >
            <span className="sr-only">拍照</span>
          </button>
        ) : (
          <button
            type="button"
            disabled={disabled}
            onClick={onNeedFallback}
            className="rounded-full bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white disabled:opacity-40"
          >
            開啟相機／相簿
          </button>
        )}
      </div>
    </div>
  );
}
