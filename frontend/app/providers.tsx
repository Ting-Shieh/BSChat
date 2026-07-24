"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Mobile soft-keyboard / tab focus often fires window focus and
            // remounts UI mid-tap; prefer stale-while-revalidate over aggressive refetch.
            refetchOnWindowFocus: false,
            refetchOnMount: true,
            staleTime: 30_000,
          },
        },
      }),
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
