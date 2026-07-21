"use client";

import { useEffect, useState } from "react";
import { cn } from "@/shared/lib/cn";

export type PlanStepStatus = "pending" | "active" | "done" | "skipped";

export interface PlanStep {
  id: number;
  title: string;
  detail?: string;
  status: PlanStepStatus;
}

const BASE_STEPS: Omit<PlanStep, "status" | "detail">[] = [
  { id: 1, title: "理解你的需求" },
  { id: 2, title: "在你的名片庫搜尋" },
  { id: 3, title: "在公開可推薦池查找" },
  { id: 4, title: "比對誰最符合" },
  { id: 5, title: "整理商機簡報" },
];

function patchStep(
  prev: PlanStep[],
  id: number,
  status: PlanStepStatus,
  detail?: string,
): PlanStep[] {
  return prev.map((s) => {
    if (s.id === id) return { ...s, status, detail: detail ?? s.detail };
    if (status === "active" && s.status === "active") return { ...s, status: "pending" };
    return s;
  });
}

/** Fixed five-step plan UX (PRD v4 §5). Step 3 skipped when public pool not available. */
export type PublicSkipReason = "trial" | "empty" | "private_only";

export function SearchPlanPanel({
  running,
  finished,
  includePublicPool,
  publicSkipReason = "trial",
  indexedHint,
}: {
  running: boolean;
  finished: boolean;
  includePublicPool: boolean;
  /** Why step 3 is skipped when includePublicPool is false */
  publicSkipReason?: PublicSkipReason;
  indexedHint?: number;
}) {
  const skipDetail =
    publicSkipReason === "empty"
      ? "略過 · 目前沒有可推薦的公開身份"
      : publicSkipReason === "private_only"
        ? "略過 · 本次只搜名片庫"
        : "略過 · 公開推薦試用已用完（終身 2 次）";

  const [steps, setSteps] = useState<PlanStep[]>(() =>
    BASE_STEPS.map((s) => ({ ...s, status: "pending" as const })),
  );
  const visible = running || finished;

  useEffect(() => {
    if (!running) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    setSteps(BASE_STEPS.map((s) => ({ ...s, status: "pending" as const })));

    const at = (ms: number, fn: () => void) => {
      timers.push(setTimeout(fn, ms));
    };

    at(150, () => setSteps((p) => patchStep(p, 1, "active")));
    at(900, () => setSteps((p) => patchStep(p, 1, "done", "解析意圖與約束")));
    at(950, () => setSteps((p) => patchStep(p, 2, "active")));
    at(1800, () =>
      setSteps((p) =>
        patchStep(
          p,
          2,
          "done",
          indexedHint != null ? `名片庫約 ${indexedHint} 位可搜尋` : "檢索你的／子團隊庫",
        ),
      ),
    );

    if (includePublicPool) {
      at(1850, () => setSteps((p) => patchStep(p, 3, "active")));
      at(2700, () => setSteps((p) => patchStep(p, 3, "done", "查詢公開可推薦身份")));
      at(2750, () => setSteps((p) => patchStep(p, 4, "active")));
      at(3500, () => setSteps((p) => patchStep(p, 4, "done", "依吻合度排序")));
      // 步驟 5 等 API finished 才打勾，避免「全勾了卻沒結果」像當機
      at(3550, () =>
        setSteps((p) => patchStep(p, 5, "active", "後端仍在整理，通常還要幾秒…")),
      );
    } else {
      at(1850, () => setSteps((p) => patchStep(p, 3, "skipped", skipDetail)));
      at(1900, () => setSteps((p) => patchStep(p, 4, "active")));
      at(2600, () => setSteps((p) => patchStep(p, 4, "done", "依吻合度排序")));
      at(2650, () =>
        setSteps((p) => patchStep(p, 5, "active", "後端仍在整理，通常還要幾秒…")),
      );
    }

    return () => timers.forEach(clearTimeout);
  }, [running, includePublicPool, indexedHint, skipDetail]);

  useEffect(() => {
    if (!finished || running) return;
    setSteps((prev) =>
      prev.map((s) => {
        if (s.id === 3 && !includePublicPool) {
          return {
            ...s,
            status: "skipped" as const,
            detail: s.detail ?? skipDetail,
          };
        }
        if (s.id === 5) {
          return { ...s, status: "done", detail: "開場白 · 理由 · 分區標示" };
        }
        if (s.status === "pending" || s.status === "active") {
          return { ...s, status: "done" };
        }
        return s;
      }),
    );
  }, [finished, running, includePublicPool, skipDetail]);

  if (!visible) return null;

  const waitingOnBackend = running && steps.some((s) => s.id === 5 && s.status === "active");

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--color-primary)] text-sm text-white">
          ✦
        </span>
        <div>
          <p className="text-[13px] font-semibold text-[var(--color-primary)]">
            {finished && !running ? "AI 計劃完成" : waitingOnBackend ? "正在整理商機簡報…" : "AI 計劃中"}
          </p>
          <p className="text-[11px] text-[var(--color-text-tertiary)]">
            {waitingOnBackend
              ? "搜尋／比對需要呼叫 AI，請稍候，完成後結果會出現在下方"
              : "固定五步 · 看得到在做什麼"}
          </p>
        </div>
      </div>

      {waitingOnBackend && (
        <p className="mb-2 animate-pulse rounded-lg bg-[var(--color-ai-bg)] px-3 py-2 text-[12px] text-[var(--color-ai-text)]">
          尚未完成：步驟 5 會等後端回應才打勾，不是當掉。
        </p>
      )}

      <ul className="mt-2 space-y-0 border-t border-[var(--color-border)] pt-1">
        {steps.map((step) => (
          <li
            key={step.id}
            className={cn(
              "flex gap-2.5 py-2 transition-opacity",
              step.status === "pending" && "opacity-35",
              step.status !== "pending" && "opacity-100",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full border text-[11px]",
                step.status === "active" &&
                  "border-[var(--color-info)] text-[var(--color-info)] shadow-[0_0_0_3px_rgba(2,132,199,0.12)]",
                step.status === "done" &&
                  "border-[var(--color-success)] bg-[var(--color-success)] text-white",
                step.status === "skipped" &&
                  "border-[var(--color-border)] bg-[#F5F5F4] text-[var(--color-text-tertiary)]",
                step.status === "pending" && "border-[var(--color-border)] bg-white",
              )}
            >
              {step.status === "done"
                ? "✓"
                : step.status === "skipped"
                  ? "–"
                  : step.status === "active"
                    ? "…"
                    : step.id}
            </span>
            <div className="min-w-0">
              <p className="text-[13.5px] font-medium text-[var(--color-text-primary)]">{step.title}</p>
              {step.detail && (
                <p className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">{step.detail}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
