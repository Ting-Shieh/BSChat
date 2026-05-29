import { LoginForm } from "@/features/auth/components/LoginForm";
import { PrivacyStrip } from "@/shared/components/PrivacyStrip";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-primary)]">BSChat</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">AI 驅動名片管理 · MVP Dev 登入</p>
      </div>
      <LoginForm />
      <PrivacyStrip />
    </main>
  );
}
