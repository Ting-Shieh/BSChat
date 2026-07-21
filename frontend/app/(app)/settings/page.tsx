import { Suspense } from "react";
import { SettingsPage } from "@/features/settings/components/SettingsPage";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-full items-center justify-center text-sm text-[var(--color-text-secondary)]">
          載入中…
        </div>
      }
    >
      <SettingsPage />
    </Suspense>
  );
}
