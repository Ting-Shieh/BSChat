import { cn } from "@/shared/lib/cn";

interface ConfidenceDotProps {
  confidence?: number;
  className?: string;
}

export function ConfidenceDot({ confidence = 1, className }: ConfidenceDotProps) {
  const low = confidence < 0.8;
  return (
    <span
      className={cn(
        "inline-block h-2 w-2 rounded-full",
        low ? "bg-amber-500" : "bg-emerald-500",
        className,
      )}
      title={low ? "低信心度" : "高信心度"}
    />
  );
}
