"use client";

export function SearchSuggestionPills({
  suggestions,
  disabled,
  onPick,
}: {
  suggestions: string[];
  disabled?: boolean;
  onPick: (query: string) => void;
}) {
  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-[var(--color-text-tertiary)]">依你的名片庫推薦</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((query) => (
          <button
            key={query}
            type="button"
            disabled={disabled}
            onClick={() => onPick(query)}
            className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-left text-xs text-[var(--color-text-secondary)] transition hover:border-[var(--color-primary)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
          >
            {query}
          </button>
        ))}
      </div>
    </div>
  );
}
