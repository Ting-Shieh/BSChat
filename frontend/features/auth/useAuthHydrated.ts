"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/store";

export function useAuthHydrated() {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const finish = () => setHydrated(true);

    if (useAuthStore.persist.hasHydrated()) {
      finish();
      return;
    }

    const unsub = useAuthStore.persist.onFinishHydration(finish);
    void Promise.resolve(useAuthStore.persist.rehydrate()).then(finish).catch(finish);

    // 安全網：避免 persist 異常時永遠卡在「載入中」
    const timer = setTimeout(finish, 1500);

    return () => {
      unsub();
      clearTimeout(timer);
    };
  }, []);

  return hydrated;
}
