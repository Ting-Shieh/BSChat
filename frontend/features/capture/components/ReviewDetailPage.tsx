"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/store";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import { resolveMediaUrl } from "@/shared/lib/media-url";
import * as captureApi from "../api";
import { useCard } from "../hooks";
import { ActionToast } from "./ActionToast";
import { DeleteCardDialog } from "./DeleteCardDialog";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]";

function str(v: unknown) {
  return typeof v === "string" ? v : "";
}

export function ReviewDetailPage() {
  const params = useParams<{ cardId: string }>();
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data: card, isLoading } = useCard(params.cardId);

  const fields = card?.ocr_result?.extracted_fields ?? {};
  const conf = card?.ocr_result?.field_confidences ?? {};

  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (card) {
      setName(str(fields.name));
      setCompany(str(fields.company));
      setTitle(str(fields.title));
    }
  }, [card, fields.name, fields.company, fields.title]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["cards"] });
    queryClient.invalidateQueries({ queryKey: ["pending-count"] });
    queryClient.invalidateQueries({ queryKey: ["contacts"] });
    queryClient.invalidateQueries({ queryKey: ["card", params.cardId] });
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  };

  const confirm = useMutation({
    mutationFn: (body: { name: string; company: string; title: string; version: number }) =>
      captureApi.reviewCard(token!, params.cardId, body),
    onSuccess: () => {
      invalidate();
      showToast("已確認 ✓");
      router.push("/review");
    },
  });

  const skip = useMutation({
    mutationFn: () => captureApi.skipReviewCard(token!, params.cardId),
    onSuccess: () => {
      invalidate();
      showToast("已跳過，仍可在搜尋中找到這位聯絡人");
      router.push("/review");
    },
  });

  const remove = useMutation({
    mutationFn: () => captureApi.deleteCard(token!, params.cardId),
    onSuccess: () => {
      invalidate();
      router.push("/review");
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!card) return;
    confirm.mutate({ name, company, title, version: card.version });
  };

  if (isLoading || !card) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  if (card.review_status === "confirmed" || card.review_status === "auto_accepted") {
    return (
      <main className="flex flex-col gap-4 p-4">
        <Link href="/review" className="text-sm text-[var(--color-primary)]">
          ← 返回列表
        </Link>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-medium">
            {card.review_status === "confirmed" ? "此名片已確認" : "此名片已自動確認"}
          </p>
          <p className="mt-1 text-emerald-800">
            {str(fields.name)} · {str(fields.company) || "—"}
          </p>
          <p className="mt-2 text-xs text-emerald-700">已收進名片庫，無需再次核對。</p>
        </div>
        <Link
          href="/contacts"
          className="rounded-xl bg-[var(--color-primary)] py-3 text-center font-medium text-white"
        >
          前往名片庫
        </Link>
      </main>
    );
  }

  const phones = Array.isArray(fields.phones) ? (fields.phones as string[]).join(" · ") : "";
  const emails = Array.isArray(fields.emails) ? (fields.emails as string[]).join(" · ") : "";
  const canSkip = card.review_status === "pending_review";
  const cardImageSrc = resolveMediaUrl(card.image_url);

  return (
    <main className="flex flex-col gap-4 p-4">
      <Link href="/review" className="text-sm text-[var(--color-primary)]">
        ← 返回列表
      </Link>

      {cardImageSrc && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={cardImageSrc}
          alt="名片"
          className="mx-auto max-h-48 rounded-lg border border-[var(--color-border)] object-contain"
        />
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {(
          [
            ["name", "姓名", name, setName],
            ["company", "公司", company, setCompany],
            ["title", "抬頭", title, setTitle],
          ] as const
        ).map(([key, label, value, setter]) => (
          <div key={key}>
            <label className="mb-1 flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <ConfidenceDot confidence={conf[key]} />
              {label}
            </label>
            <input value={value} onChange={(e) => setter(e.target.value)} className={inputClass} />
          </div>
        ))}

        {(phones || emails || str(fields.address) || str(fields.website)) && (
          <div className="rounded-lg bg-[var(--color-primary-muted)] p-3 text-sm text-[var(--color-text-secondary)]">
            {phones && <p>電話：{phones}</p>}
            {emails && <p>Email：{emails}</p>}
            {str(fields.address) && <p>地址：{str(fields.address)}</p>}
            {str(fields.website) && <p>網站：{str(fields.website)}</p>}
            <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">（唯讀，確認後寫入聯絡人）</p>
          </div>
        )}

        {confirm.error && (
          <p className="text-sm text-[var(--color-error)]">確認失敗，請重試</p>
        )}
        {skip.error && (
          <p className="text-sm text-[var(--color-error)]">無法跳過這張名片</p>
        )}

        <button
          type="submit"
          disabled={confirm.isPending}
          className="rounded-xl bg-[var(--color-primary)] py-3 font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
        >
          {confirm.isPending ? "儲存中…" : "確認"}
        </button>

        {canSkip && (
          <button
            type="button"
            disabled={skip.isPending}
            onClick={() => skip.mutate()}
            className="rounded-xl border border-[var(--color-border)] py-3 text-sm text-[var(--color-text-primary)] disabled:opacity-50"
          >
            {skip.isPending ? "處理中…" : "稍後再確認"}
          </button>
        )}

        <button
          type="button"
          onClick={() => setDeleteOpen(true)}
          className="py-1 text-sm text-[var(--color-error)]"
        >
          刪除這張名片
        </button>
      </form>

      <DeleteCardDialog
        open={deleteOpen}
        name={name || "—"}
        company={company || "—"}
        pending={remove.isPending}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => remove.mutate()}
      />
      <ActionToast message={toast} />
    </main>
  );
}
