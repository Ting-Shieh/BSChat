"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useAuthStore } from "@/features/auth/store";

function subscribeHydration(onStoreChange: () => void) {
  return useAuthStore.persist.onFinishHydration(onStoreChange);
}

function getHydrationSnapshot() {
  return useAuthStore.persist.hasHydrated();
}

/** Wait until zustand persist has restored token from localStorage. */
export function useAuthHydrated() {
  const persistHydrated = useSyncExternalStore(
    subscribeHydration,
    getHydrationSnapshot,
    () => false,
  );
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) return;
    void Promise.resolve(useAuthStore.persist.rehydrate()).catch(() => undefined);
    // Unblock UI if persist never finishes (stale SW / blocked storage).
    const timer = window.setTimeout(() => setTimedOut(true), 2500);
    return () => window.clearTimeout(timer);
  }, []);

  return persistHydrated || timedOut;
}
