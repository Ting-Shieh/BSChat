"use client";

import { FormEvent, useEffect, useState } from "react";
import type { ContactDetail } from "@/shared/types/contact";

const inputClass =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-primary)]";

type Props = {
  contact: ContactDetail;
  open: boolean;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (fields: {
    display_name: string;
    company_name: string;
    title: string;
    phone: string;
    email: string;
    address: string;
    website: string;
    linkedin_url: string;
  }) => void;
};

export function ContactEditSheet({ contact, open, saving, error, onClose, onSave }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [title, setTitle] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [website, setWebsite] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");

  useEffect(() => {
    if (!open) return;
    setDisplayName(contact.display_name ?? "");
    setCompanyName(contact.company_name ?? "");
    setTitle(contact.title ?? "");
    setPhone(contact.phones?.[0]?.value ?? "");
    setEmail(contact.emails?.[0]?.value ?? "");
    setAddress(contact.address ?? "");
    setWebsite(contact.website ?? "");
    setLinkedinUrl(contact.linkedin_url ?? "");
  }, [open, contact]);

  if (!open) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSave({
      display_name: displayName.trim(),
      company_name: companyName.trim(),
      title: title.trim(),
      phone: phone.trim(),
      email: email.trim(),
      address: address.trim(),
      website: website.trim(),
      linkedin_url: linkedinUrl.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
      <button
        type="button"
        className="absolute inset-0"
        aria-label="關閉"
        onClick={onClose}
      />
      <form
        onSubmit={handleSubmit}
        className="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-lg sm:rounded-2xl"
      >
        <h2 className="mb-1 text-base font-medium text-[var(--color-text-primary)]">編輯聯絡人</h2>
        <p className="mb-4 text-xs text-[var(--color-text-tertiary)]">
          修改公司名稱後，系統會重新補全公司資訊。
        </p>

        <div className="space-y-3">
          <Field label="姓名" value={displayName} onChange={setDisplayName} required />
          <Field label="公司" value={companyName} onChange={setCompanyName} />
          <Field label="職稱" value={title} onChange={setTitle} />
          <Field label="電話" value={phone} onChange={setPhone} />
          <Field label="Email" value={email} onChange={setEmail} type="email" />
          <Field label="地址" value={address} onChange={setAddress} />
          <Field label="網站" value={website} onChange={setWebsite} />
          <Field label="LinkedIn" value={linkedinUrl} onChange={setLinkedinUrl} placeholder="https://linkedin.com/in/..." />
        </div>

        {error && (
          <p className="mt-3 text-xs text-[var(--color-accent-hover)]" role="alert">
            {error}
          </p>
        )}

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="flex-1 rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-secondary)]"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={saving || !displayName.trim()}
            className="flex-1 rounded-lg bg-[var(--color-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "儲存中…" : "儲存"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-[var(--color-text-secondary)]">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className={inputClass}
      />
    </label>
  );
}
