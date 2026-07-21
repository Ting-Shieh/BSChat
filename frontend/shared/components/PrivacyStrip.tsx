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
      僅子團隊可見 · 不對外公開搜尋 · 不存取他人私人資料
    </p>
  );
}
