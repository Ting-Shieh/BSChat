"use client";

import { useCallback, useState } from "react";

export function useCopyContact() {
  const [message, setMessage] = useState<string | null>(null);

  const copy = useCallback(async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(`已複製${label}`);
      window.setTimeout(() => setMessage(null), 2500);
      return true;
    } catch {
      setMessage("複製失敗，請手動選取");
      window.setTimeout(() => setMessage(null), 2500);
      return false;
    }
  }, []);

  return { copy, message, clearMessage: () => setMessage(null) };
}
