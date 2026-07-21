"use client";

import {
  useAcceptNotification,
  useMarkNotificationRead,
  useNotifications,
} from "@/features/subteam/hooks";
import { ApiError } from "@/shared/lib/api-client";

const STATUS_HINT: Record<string, string> = {
  NOT_ORG_MEMBER: "對方須先是企業成員",
  INVITE_NOT_USABLE: "邀請已失效",
  EMAIL_MISMATCH: "此邀請不是發給你的帳號",
  ALREADY_MEMBER: "你已在此子團隊",
};

export function NotificationsPanel() {
  const { data, isLoading } = useNotifications();
  const accept = useAcceptNotification();
  const markRead = useMarkNotificationRead();

  if (isLoading) {
    return <p className="text-xs text-[var(--color-text-secondary)]">載入通知…</p>;
  }

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  if (items.length === 0) {
    return null;
  }

  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">通知</h2>
        {unread > 0 && (
          <span className="rounded-full bg-[var(--color-primary-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-primary)]">
            {unread} 未讀
          </span>
        )}
      </div>
      <ul className="space-y-2">
        {items.slice(0, 8).map((n) => {
          const isInvite = n.kind === "sub_team_invite";
          const unreadRow = !n.read_at;
          return (
            <li
              key={n.id}
              className={`rounded-lg border px-3 py-2.5 ${
                unreadRow
                  ? "border-[var(--color-primary)]/30 bg-[var(--color-primary-muted)]/40"
                  : "border-[var(--color-border)]"
              }`}
            >
              <p className="text-sm font-semibold text-[var(--color-text-primary)]">{n.title}</p>
              {n.body && (
                <p className="mt-0.5 text-[12px] text-[var(--color-text-secondary)]">{n.body}</p>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                {isInvite && unreadRow && (
                  <button
                    type="button"
                    disabled={accept.isPending}
                    className="rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                    onClick={() => {
                      accept.mutate(n.id, {
                        onError: (e) => {
                          let code =
                            e instanceof ApiError ? e.message : "無法接受邀請";
                          try {
                            const p = JSON.parse(code) as { detail?: string };
                            if (p.detail) code = p.detail;
                          } catch {
                            /* keep */
                          }
                          window.alert(STATUS_HINT[code] ?? code);
                        },
                      });
                    }}
                  >
                    接受加入
                  </button>
                )}
                {unreadRow && (
                  <button
                    type="button"
                    className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)]"
                    onClick={() => markRead.mutate(n.id)}
                  >
                    標為已讀
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
