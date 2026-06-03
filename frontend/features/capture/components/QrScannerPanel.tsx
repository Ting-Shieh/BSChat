"use client";

import { useEffect, useRef, useState } from "react";
import { Scanner, type IDetectedBarcode } from "@yudiel/react-qr-scanner";
import { cn } from "@/shared/lib/cn";

export type ScanPhase = "idle" | "detected" | "importing";

export type QrBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

function QrViewfinder({ phase, qrBox }: { phase: ScanPhase; qrBox: QrBox | null }) {
  const locked = phase === "detected" || phase === "importing";
  const borderColor = locked ? "border-emerald-400" : "border-sky-400";
  const corner = cn("absolute h-7 w-7 border-[3px]", borderColor);

  return (
    <div className="pointer-events-none absolute inset-0 z-10">
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className={cn(
            "relative h-56 w-56 rounded-lg transition-all duration-200",
            locked && "scale-[1.02]",
          )}
          style={{ boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.55)" }}
        >
          <div className={cn(corner, "left-0 top-0 rounded-tl-lg border-b-0 border-r-0")} />
          <div className={cn(corner, "right-0 top-0 rounded-tr-lg border-b-0 border-l-0")} />
          <div className={cn(corner, "bottom-0 left-0 rounded-bl-lg border-r-0 border-t-0")} />
          <div className={cn(corner, "bottom-0 right-0 rounded-br-lg border-l-0 border-t-0")} />
          {!locked && (
            <div className="absolute inset-x-2 top-2 h-0.5 animate-[qr-scan_2.2s_ease-in-out_infinite] rounded-full bg-sky-400/90 shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
          )}
          {locked && (
            <div className="absolute inset-0 rounded-lg border-2 border-emerald-400/80 bg-emerald-400/10" />
          )}
        </div>
      </div>
      {qrBox && locked && (
        <div
          className="absolute rounded-md border-2 border-sky-300 bg-sky-400/15 shadow-[0_0_12px_rgba(56,189,248,0.6)] transition-all duration-150"
          style={{
            left: qrBox.x,
            top: qrBox.y,
            width: qrBox.width,
            height: qrBox.height,
          }}
        />
      )}
    </div>
  );
}

export function QrScannerPanel({
  phase,
  paused,
  onDetect,
  onError,
}: {
  phase: ScanPhase;
  paused: boolean;
  onDetect: (code: IDetectedBarcode) => void;
  onError: (message: string) => void;
}) {
  const handlingRef = useRef(false);
  const [qrBox, setQrBox] = useState<QrBox | null>(null);

  useEffect(() => {
    if (!paused && phase === "idle") {
      handlingRef.current = false;
      setQrBox(null);
    }
  }, [paused, phase]);

  return (
    <div className="relative h-full w-full">
      <Scanner
        formats={["qr_code"]}
        paused={paused}
        sound={false}
        allowMultiple={false}
        scanDelay={400}
        constraints={{ facingMode: { ideal: "environment" } }}
        onScan={(codes) => {
          if (paused || handlingRef.current || codes.length === 0) return;
          const code = codes[0];
          if (!code.rawValue?.trim()) return;
          handlingRef.current = true;
          if (code.boundingBox) {
            setQrBox({
              x: code.boundingBox.x,
              y: code.boundingBox.y,
              width: code.boundingBox.width,
              height: code.boundingBox.height,
            });
          }
          onDetect(code);
        }}
        onError={(err) => onError(err.message ?? "無法開啟相機")}
        components={{
          onOff: false,
          torch: false,
          zoom: false,
          finder: false,
        }}
        styles={{
          container: { width: "100%", height: "100%", position: "relative" },
          video: { width: "100%", height: "100%", objectFit: "cover" },
        }}
      />
      <QrViewfinder phase={phase} qrBox={qrBox} />
    </div>
  );
}
