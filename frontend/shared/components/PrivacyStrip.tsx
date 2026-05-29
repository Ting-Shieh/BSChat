import { cn } from "@/shared/lib/cn";

interface PrivacyStripProps {
  className?: string;
}

export function PrivacyStrip({ className }: PrivacyStripProps) {
  return (
    <p
      className={cn(
        "rounded-lg bg-[var(--color-privacy-bg)] px-3 py-2 text-xs text-[var(--color-privacy-text)]",
        className,
      )}
    >
      僅搜尋您的人脈與自願公開的商務身份 · 不存取他人私人資料
    </p>
  );
}
