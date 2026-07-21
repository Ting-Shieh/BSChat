"use client";

import { useState } from "react";
import { SearchSuggestionPills } from "./SearchSuggestionPills";

export function SearchInput({
  disabled,
  onSubmit,
  suggestions = [],
  value: controlledValue,
  onValueChange,
  placeholder = "追問或開新搜尋…",
  showSuggestions = false,
  submitLabel = "送出",
}: {
  disabled?: boolean;
  onSubmit: (query: string) => void;
  suggestions?: string[];
  value?: string;
  onValueChange?: (query: string) => void;
  placeholder?: string;
  /** Sample pills — only for empty-thread first ask */
  showSuggestions?: boolean;
  submitLabel?: string;
}) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;

  const setValue = (next: string) => {
    if (controlledValue === undefined) {
      setInternalValue(next);
    }
    onValueChange?.(next);
  };

  const submit = () => {
    const q = value.trim();
    if (!q || disabled) return;
    onSubmit(q);
  };

  return (
    <div className="flex flex-col gap-2">
      {showSuggestions && suggestions.length > 0 && (
        <SearchSuggestionPills
          suggestions={suggestions}
          disabled={disabled}
          onPick={setValue}
        />
      )}
      <form
        className="flex items-end gap-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-2 shadow-sm"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          enterKeyHint="send"
          className="min-w-0 flex-1 bg-transparent px-1.5 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="shrink-0 rounded-xl bg-[var(--color-primary)] px-3.5 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
        >
          {submitLabel}
        </button>
      </form>
    </div>
  );
}
