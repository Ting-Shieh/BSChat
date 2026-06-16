"use client";

import { useMemo, useState } from "react";
import { useMe } from "@/features/auth/hooks";
import {
  useCreateStub,
  useDeleteStub,
  useImportStubsCsv,
  useMyOrgs,
  useOrgStubs,
  usePublishStub,
  useUnpublishStub,
  useUpdateStub,
} from "@/features/org/hooks";
import type { PublicStub } from "@/features/org/api";
import { cn } from "@/shared/lib/cn";

const EMPTY_FORM = {
  display_name: "",
  company_name: "",
  title: "",
  responsibility_keywords: "",
  product_keywords: "",
  external_card_url: "",
};

type FormState = typeof EMPTY_FORM;
type PageTab = "list" | "create" | "import";
type ListFilter = "all" | "published" | "draft" | "unpublished";

const PAGE_TABS: { id: PageTab; label: string }[] = [
  { id: "list", label: "列表" },
  { id: "create", label: "新增" },
  { id: "import", label: "匯入" },
];

const LIST_FILTERS: { id: ListFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "published", label: "已發布" },
  { id: "draft", label: "草稿" },
  { id: "unpublished", label: "已下架" },
];

function splitKeywords(value: string) {
  return value
    .split(/[,;|]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function stubToForm(stub: PublicStub): FormState {
  return {
    display_name: stub.display_name,
    company_name: stub.company_name,
    title: stub.title ?? "",
    responsibility_keywords: stub.responsibility_keywords.join(", "),
    product_keywords: stub.product_keywords.join(", "),
    external_card_url: stub.external_card_url,
  };
}

function formToPayload(form: FormState) {
  return {
    display_name: form.display_name,
    company_name: form.company_name,
    title: form.title || null,
    responsibility_keywords: splitKeywords(form.responsibility_keywords),
    product_keywords: splitKeywords(form.product_keywords),
    external_card_url: form.external_card_url,
  };
}

export function OrgAdminPage() {
  const { data: me } = useMe();
  const { data: orgs, isLoading: orgsLoading } = useMyOrgs();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [pageTab, setPageTab] = useState<PageTab>("list");
  const [listFilter, setListFilter] = useState<ListFilter>("all");
  const [editingStubId, setEditingStubId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<FormState>(EMPTY_FORM);

  const activeOrgId = orgId ?? orgs?.items[0]?.id ?? null;
  const statusQuery = listFilter === "all" ? undefined : listFilter;
  const { data: stubs, isLoading: stubsLoading } = useOrgStubs(activeOrgId, statusQuery);
  const createStub = useCreateStub(activeOrgId ?? "");
  const updateStub = useUpdateStub(activeOrgId ?? "");
  const publishStub = usePublishStub(activeOrgId ?? "");
  const unpublishStub = useUnpublishStub(activeOrgId ?? "");
  const deleteStubMut = useDeleteStub(activeOrgId ?? "");
  const importCsv = useImportStubsCsv(activeOrgId ?? "");

  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<string | null>(null);

  const isEnterprise = me?.plan_tier === "enterprise";
  const busy =
    createStub.isPending ||
    updateStub.isPending ||
    publishStub.isPending ||
    unpublishStub.isPending ||
    deleteStubMut.isPending ||
    importCsv.isPending;

  const activeOrg = useMemo(
    () => orgs?.items.find((o) => o.id === activeOrgId),
    [orgs, activeOrgId],
  );

  const editingStub = useMemo(
    () => stubs?.items.find((s) => s.id === editingStubId) ?? null,
    [stubs, editingStubId],
  );

  if (!me || orgsLoading) {
    return (
      <div className="flex min-h-full items-center justify-center py-16 text-sm text-[var(--color-text-secondary)]">
        載入中…
      </div>
    );
  }

  if (!isEnterprise) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8">
        <h1 className="text-lg font-semibold">企業公開目錄</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          此功能需要<strong className="font-medium">企業版</strong>方案。請在設定頁切換方案，或使用 dev 登入時選 enterprise + seed_org。
        </p>
      </div>
    );
  }

  if (!activeOrgId || !orgs?.items.length) {
    return (
      <div className="mx-auto max-w-xl px-4 py-8">
        <h1 className="text-lg font-semibold">企業公開目錄</h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          尚未加入任何組織。Dev 環境請用 <code className="text-xs">seed_org: acme-demo</code> 登入。
        </p>
      </div>
    );
  }

  const startEdit = (stub: PublicStub) => {
    setEditingStubId(stub.id);
    setEditForm(stubToForm(stub));
    setEditError(null);
  };

  const cancelEdit = () => {
    setEditingStubId(null);
    setEditForm(EMPTY_FORM);
    setEditError(null);
  };

  const submitCreate = () => {
    setError(null);
    createStub.mutate(formToPayload(form), {
      onSuccess: () => {
        setForm(EMPTY_FORM);
        setPageTab("list");
        setListFilter("draft");
      },
      onError: (e) => setError(e.message),
    });
  };

  const submitEdit = () => {
    if (!editingStubId) return;
    setEditError(null);
    updateStub.mutate(
      { stubId: editingStubId, body: formToPayload(editForm) },
      {
        onSuccess: () => cancelEdit(),
        onError: (e) => setEditError(e.message),
      },
    );
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col px-4 pb-5 pt-4">
      <div className="shrink-0">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">企業公開目錄</h1>
        {activeOrg && (
          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
            {activeOrg.name} · 已發布 {activeOrg.published_stub_count} 筆
          </p>
        )}
      </div>

      {orgs.items.length > 1 && (
        <select
          value={activeOrgId}
          onChange={(e) => {
            setOrgId(e.target.value);
            cancelEdit();
          }}
          className="mt-3 w-full shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
        >
          {orgs.items.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}（已發布 {o.published_stub_count}）
            </option>
          ))}
        </select>
      )}

      <nav
        className="mt-4 flex shrink-0 border-b border-[var(--color-border)]"
        aria-label="公開目錄功能"
      >
        {PAGE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setPageTab(tab.id);
              cancelEdit();
            }}
            className={cn(
              "flex-1 border-b-2 py-2.5 text-sm font-medium transition-colors",
              pageTab === tab.id
                ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="mt-4 min-h-0 flex-1">
        {pageTab === "list" && (
          <ListPanel
            filter={listFilter}
            onFilterChange={(f) => {
              setListFilter(f);
              cancelEdit();
            }}
            stubs={stubs?.items ?? []}
            loading={stubsLoading}
            busy={busy}
            editingStubId={editingStubId}
            editForm={editForm}
            editError={editError}
            editingStatus={editingStub?.status}
            onEdit={startEdit}
            onCancelEdit={cancelEdit}
            onEditFormChange={setEditForm}
            onSaveEdit={submitEdit}
            onPublish={(id) => publishStub.mutate(id)}
            onUnpublish={(id) => unpublishStub.mutate(id)}
            onDelete={(id) => deleteStubMut.mutate(id)}
          />
        )}

        {pageTab === "create" && (
          <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <p className="text-xs text-[var(--color-text-tertiary)]">
              建立後為草稿；到「列表 → 草稿」可發布。
            </p>
            <StubForm form={form} onChange={setForm} className="mt-3" />
            {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
            <button
              type="button"
              disabled={busy || !form.display_name || !form.company_name || !form.external_card_url}
              onClick={submitCreate}
              className="mt-4 w-full rounded-lg bg-[var(--color-primary)] px-3 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              建立草稿
            </button>
          </section>
        )}

        {pageTab === "import" && (
          <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <p className="text-xs text-[var(--color-text-tertiary)]">
              CSV 表頭：display_name, company_name, title, responsibility_keywords, product_keywords,
              external_card_url
            </p>
            <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">
              關鍵字可用分號分隔。匯入後為草稿，需至列表手動發布。
            </p>
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={busy}
              className="mt-4 block w-full text-sm"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setImportResult(null);
                importCsv.mutate(
                  { file, autoPublish: false },
                  {
                    onSuccess: (r) => {
                      setImportResult(`匯入 ${r.imported} 筆，略過 ${r.skipped} 筆`);
                      setPageTab("list");
                      setListFilter("draft");
                    },
                    onError: (err) => setImportResult(err.message),
                  },
                );
                e.target.value = "";
              }}
            />
            {importResult && (
              <p className="mt-3 text-sm text-[var(--color-text-secondary)]">{importResult}</p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function ListPanel({
  filter,
  onFilterChange,
  stubs,
  loading,
  busy,
  editingStubId,
  editForm,
  editError,
  editingStatus,
  onEdit,
  onCancelEdit,
  onEditFormChange,
  onSaveEdit,
  onPublish,
  onUnpublish,
  onDelete,
}: {
  filter: ListFilter;
  onFilterChange: (f: ListFilter) => void;
  stubs: PublicStub[];
  loading: boolean;
  busy: boolean;
  editingStubId: string | null;
  editForm: FormState;
  editError: string | null;
  editingStatus?: PublicStub["status"];
  onEdit: (stub: PublicStub) => void;
  onCancelEdit: () => void;
  onEditFormChange: (form: FormState) => void;
  onSaveEdit: () => void;
  onPublish: (id: string) => void;
  onUnpublish: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const canSaveEdit =
    !!editForm.display_name && !!editForm.company_name && !!editForm.external_card_url;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {LIST_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => onFilterChange(f.id)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              filter === f.id
                ? "bg-[var(--color-primary)] text-white"
                : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        {loading ? (
          <p className="text-xs text-[var(--color-text-tertiary)]">載入中…</p>
        ) : stubs.length === 0 ? (
          <p className="text-xs text-[var(--color-text-tertiary)]">
            {filter === "all" ? "尚無公開身份" : `沒有「${LIST_FILTERS.find((x) => x.id === filter)?.label}」項目`}
          </p>
        ) : (
          <ul className="space-y-3">
            {stubs.map((stub) => {
              const isEditing = editingStubId === stub.id;
              return (
                <li key={stub.id} className="rounded-lg border border-[var(--color-border)] p-3">
                  {isEditing ? (
                    <div>
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">編輯公開身份</p>
                      {editingStatus === "published" && (
                        <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">
                          已發布項目儲存後會自動更新搜尋索引。
                        </p>
                      )}
                      <StubForm form={editForm} onChange={onEditFormChange} className="mt-3" />
                      {editError && <p className="mt-2 text-xs text-red-600">{editError}</p>}
                      <div className="mt-4 flex gap-2">
                        <button
                          type="button"
                          disabled={busy || !canSaveEdit}
                          onClick={onSaveEdit}
                          className="flex-1 rounded-lg bg-[var(--color-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                        >
                          儲存
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={onCancelEdit}
                          className="rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-secondary)] disabled:opacity-50"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{stub.display_name}</p>
                          <p className="text-xs text-[var(--color-text-secondary)]">
                            {stub.company_name} · {stub.title ?? "—"}
                          </p>
                          <StatusBadge status={stub.status} />
                        </div>
                        <div className="flex shrink-0 flex-col gap-1">
                          <ActionBtn label="編輯" disabled={busy} onClick={() => onEdit(stub)} />
                          {stub.status === "draft" && (
                            <>
                              <ActionBtn label="發布" disabled={busy} onClick={() => onPublish(stub.id)} />
                              <ActionBtn
                                label="刪除"
                                disabled={busy}
                                variant="muted"
                                onClick={() => onDelete(stub.id)}
                              />
                            </>
                          )}
                          {stub.status === "published" && (
                            <ActionBtn
                              label="下架"
                              disabled={busy}
                              variant="muted"
                              onClick={() => onUnpublish(stub.id)}
                            />
                          )}
                          {stub.status === "unpublished" && (
                            <ActionBtn label="重新發布" disabled={busy} onClick={() => onPublish(stub.id)} />
                          )}
                        </div>
                      </div>
                      <p className="mt-2 truncate text-[10px] text-[var(--color-text-tertiary)]">
                        {stub.external_card_url}
                      </p>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function StubForm({
  form,
  onChange,
  className,
}: {
  form: FormState;
  onChange: (form: FormState) => void;
  className?: string;
}) {
  return (
    <div className={cn("grid gap-2", className)}>
      <Field label="姓名" value={form.display_name} onChange={(v) => onChange({ ...form, display_name: v })} />
      <Field label="公司" value={form.company_name} onChange={(v) => onChange({ ...form, company_name: v })} />
      <Field label="職稱" value={form.title} onChange={(v) => onChange({ ...form, title: v })} />
      <Field
        label="職責關鍵字（逗號分隔）"
        value={form.responsibility_keywords}
        onChange={(v) => onChange({ ...form, responsibility_keywords: v })}
      />
      <Field
        label="產品關鍵字（逗號分隔）"
        value={form.product_keywords}
        onChange={(v) => onChange({ ...form, product_keywords: v })}
      />
      <Field
        label="外部名片 URL（必填）"
        value={form.external_card_url}
        onChange={(v) => onChange({ ...form, external_card_url: v })}
      />
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block text-xs">
      <span className="text-[var(--color-text-secondary)]">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
      />
    </label>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "mt-1 inline-block rounded px-1.5 py-0.5 text-[10px]",
        status === "published" && "bg-green-100 text-green-800",
        status === "draft" && "bg-amber-100 text-amber-800",
        status === "unpublished" && "bg-gray-100 text-gray-600",
      )}
    >
      {status === "published" ? "已發布" : status === "draft" ? "草稿" : "已下架"}
    </span>
  );
}

function ActionBtn({
  label,
  onClick,
  disabled,
  variant = "primary",
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: "primary" | "muted";
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded px-2 py-1 text-[10px] font-medium disabled:opacity-50",
        variant === "primary"
          ? "bg-[var(--color-primary)] text-white"
          : "border border-[var(--color-border)] text-[var(--color-text-secondary)]",
      )}
    >
      {label}
    </button>
  );
}
