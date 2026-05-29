"use client";

import { useState } from "react";
import { SearchSuggestionPills } from "./SearchSuggestionPills";

const SEARCH_PLACEHOLDER = "用自然語言描述你要找的人或情境…";

export function SearchInput({
  disabled,
  onSubmit,
  suggestions = [],
  value: controlledValue,
  onValueChange,
}: {
  disabled?: boolean;
  onSubmit: (query: string) => void;
  suggestions?: string[];
  value?: string;
  onValueChange?: (query: string) => void;
}) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;

  const setValue = (next: string) => {
    if (controlledValue === undefined) {
      setInternalValue(next);
    }
    onValueChange?.(next);
  };

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim();
        if (q) onSubmit(q);
      }}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={SEARCH_PLACEHOLDER}
        rows={3}
        disabled={disabled}
        className="w-full resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-primary)] focus:outline-none disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-xl bg-[var(--color-primary)] py-3 text-sm font-medium text-white disabled:opacity-50"
      >
        搜尋
      </button>
      <SearchSuggestionPills
        suggestions={suggestions}
        disabled={disabled}
        onPick={setValue}
      />
    </form>
  );
}
