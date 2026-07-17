"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/features/auth/store";

function CallbackBody() {
  const params = useSearchParams();
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);

  useEffect(() => {
    const token = params.get("access_token");
    const next = params.get("next") || "/contacts";
    if (!token) {
      router.replace("/login");
      return;
    }
    setToken(token);
    router.replace(next.startsWith("/") ? next : "/contacts");
  }, [params, router, setToken]);

  return <p className="text-sm text-[var(--color-text-secondary)]">登入中…</p>;
}

export default function AuthCallbackPage() {
  return (
    <main className="flex min-h-full flex-1 items-center justify-center px-6 py-12">
      <Suspense fallback={<p className="text-sm text-[var(--color-text-secondary)]">登入中…</p>}>
        <CallbackBody />
      </Suspense>
    </main>
  );
}
