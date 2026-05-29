import { cn } from "@/shared/lib/cn";

interface EmptyStateProps {
  title: string;
  description?: string;
  className?: string;
}

export function EmptyState({ title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center",
        className,
      )}
    >
      <p className="text-base font-medium text-[var(--color-text-primary)]">{title}</p>
      {description && (
        <p className="max-w-xs text-sm text-[var(--color-text-secondary)]">{description}</p>
      )}
    </div>
  );
}
