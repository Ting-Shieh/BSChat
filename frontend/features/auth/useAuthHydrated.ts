"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/store";

/** Wait until zustand persist has restored token from localStorage. */
export function useAuthHydrated() {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const finish = () => {
      if (!cancelled) setHydrated(true);
    };

    if (useAuthStore.persist.hasHydrated()) {
      finish();
      return;
    }

    const unsub = useAuthStore.persist.onFinishHydration(finish);
    void useAuthStore.persist.rehydrate().then(finish).catch(finish);

    // Last-resort only — do not race ahead of localStorage restore on slow devices.
    const timer = setTimeout(finish, 5000);

    return () => {
      cancelled = true;
      unsub();
      clearTimeout(timer);
    };
  }, []);

  return hydrated;
}
