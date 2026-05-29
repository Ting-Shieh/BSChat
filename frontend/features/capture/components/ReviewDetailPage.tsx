"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/store";
import { ConfidenceDot } from "@/shared/components/ConfidenceDot";
import * as captureApi from "../api";
import { useCard } from "../hooks";

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

  useEffect(() => {
    if (card) {
      setName(str(fields.name));
      setCompany(str(fields.company));
      setTitle(str(fields.title));
    }
  }, [card, fields.name, fields.company, fields.title]);

  const mutation = useMutation({
    mutationFn: (body: { name: string; company: string; title: string; version: number }) =>
      captureApi.reviewCard(token!, params.cardId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cards"] });
      queryClient.invalidateQueries({ queryKey: ["pending-count"] });
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      router.push("/review");
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!card) return;
    mutation.mutate({ name, company, title, version: card.version });
  };

  if (isLoading || !card) {
    return <main className="p-4 text-sm text-[var(--color-text-secondary)]">載入中…</main>;
  }

  const phones = Array.isArray(fields.phones) ? (fields.phones as string[]).join(" · ") : "";
  const emails = Array.isArray(fields.emails) ? (fields.emails as string[]).join(" · ") : "";

  return (
    <main className="flex flex-col gap-4 p-4">
      <Link href="/review" className="text-sm text-[var(--color-primary)]">
        ← 返回列表
      </Link>

      {card.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={card.image_url}
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

        {(phones || emails) && (
          <div className="rounded-lg bg-[var(--color-primary-muted)] p-3 text-sm text-[var(--color-text-secondary)]">
            {phones && <p>電話：{phones}</p>}
            {emails && <p>Email：{emails}</p>}
            <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">（唯讀，確認後由 M3 結構化）</p>
          </div>
        )}

        {mutation.error && (
          <p className="text-sm text-[var(--color-error)]">確認失敗，請重試</p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-xl bg-[var(--color-primary)] py-3 font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50"
        >
          {mutation.isPending ? "儲存中…" : "確認"}
        </button>
      </form>
    </main>
  );
}
