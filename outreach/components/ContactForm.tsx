"use client";

import { CONTACT_STATUSES, STATUS_LABELS, type ContactStatus } from "@/lib/labels";

export type ContactFormValues = {
  fullName: string;
  linkedinId: string;
  linkedinUrl: string;
  headline: string;
  occupation: string;
  company: string;
  industry: string;
  location: string;
  interestsText: string;
  notes: string;
  status: ContactStatus;
};

export const emptyContactForm: ContactFormValues = {
  fullName: "",
  linkedinId: "",
  linkedinUrl: "",
  headline: "",
  occupation: "",
  company: "",
  industry: "",
  location: "",
  interestsText: "",
  notes: "",
  status: "NEW",
};

export function ContactForm({
  values,
  onChange,
  onSubmit,
  submitLabel,
  pending,
  error,
  showStatus = false,
}: {
  values: ContactFormValues;
  onChange: (values: ContactFormValues) => void;
  onSubmit: () => void;
  submitLabel: string;
  pending: boolean;
  error: string;
  showStatus?: boolean;
}) {
  function set<K extends keyof ContactFormValues>(key: K, value: ContactFormValues[K]) {
    onChange({ ...values, [key]: value });
  }

  return (
    <form
      className="grid gap-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Field label="ФИО" value={values.fullName} onChange={(value) => set("fullName", value)} required />
      <Field
        label="LinkedIn ID"
        value={values.linkedinId}
        onChange={(value) => set("linkedinId", value)}
        required
        hint="Публичный идентификатор профиля, например anna-sokolova"
      />
      <Field label="Ссылка на профиль" value={values.linkedinUrl} onChange={(value) => set("linkedinUrl", value)} />
      <Field label="Заголовок профиля" value={values.headline} onChange={(value) => set("headline", value)} />
      <Field label="Род занятий" value={values.occupation} onChange={(value) => set("occupation", value)} required />
      <Field label="Компания" value={values.company} onChange={(value) => set("company", value)} />
      <Field label="Отрасль" value={values.industry} onChange={(value) => set("industry", value)} />
      <Field label="Город" value={values.location} onChange={(value) => set("location", value)} />
      <label className="sm:col-span-2">
        <span className="label">Интересы, задачи, боли</span>
        <textarea
          className="field min-h-24"
          value={values.interestsText}
          onChange={(event) => set("interestsText", event.target.value)}
          placeholder={"Каждый пункт с новой строки"}
        />
      </label>
      <label className="sm:col-span-2">
        <span className="label">Заметки</span>
        <textarea className="field min-h-24" value={values.notes} onChange={(event) => set("notes", event.target.value)} />
      </label>
      {showStatus ? (
        <label>
          <span className="label">Статус</span>
          <select className="field" value={values.status} onChange={(event) => set("status", event.target.value as ContactStatus)}>
            {CONTACT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {error ? <p className="text-sm text-red-700 sm:col-span-2">{error}</p> : null}
      <div className="sm:col-span-2">
        <button className="btn-primary" type="submit" disabled={pending}>
          {pending ? "Сохранение…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  required = false,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  hint?: string;
}) {
  return (
    <label>
      <span className="label">
        {label}
        {required ? " *" : ""}
      </span>
      <input className="field" value={value} onChange={(event) => onChange(event.target.value)} required={required} />
      {hint ? <span className="mt-1 block text-xs text-stone-500">{hint}</span> : null}
    </label>
  );
}
