"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ContactForm, type ContactFormValues } from "@/components/ContactForm";
import { StatusBadge } from "@/components/StatusBadge";
import { apiJson, type ContactDetails, type ContactDto, type DraftDto } from "@/lib/client";
import { MESSAGE_TONES, TONE_LABELS, formatDate, type MessageTone } from "@/lib/labels";
import { linesToList, listToLines } from "@/lib/text";

const SENT_REMINDER = "Убедитесь, что вы отправили сообщение вручную в LinkedIn.";

export function ContactScreen({ id }: { id: string }) {
  const router = useRouter();
  const [contact, setContact] = useState<ContactDetails | null>(null);
  const [form, setForm] = useState<ContactFormValues | null>(null);
  const [missing, setMissing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [goal, setGoal] = useState("");
  const [tone, setTone] = useState<MessageTone>("PROFESSIONAL");
  const [language, setLanguage] = useState("ru");
  const [extra, setExtra] = useState("");
  const [active, setActive] = useState<DraftDto | null>(null);
  const [text, setText] = useState("");
  const [feedback, setFeedback] = useState("");
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState("");
  const [confirmSent, setConfirmSent] = useState(false);

  useEffect(() => {
    void apiJson<ContactDetails>(`/api/contacts/${id}`)
      .then((payload) => {
        setContact(payload);
        setForm(toForm(payload));
        selectDraft(payload.drafts[0] ?? null);
      })
      .catch((reason: unknown) => {
        setMissing(true);
        setError(reason instanceof Error ? reason.message : "Контакт не найден");
      });
  }, [id]);

  function selectDraft(draft: DraftDto | null) {
    setActive(draft);
    setText(draft?.generatedText ?? "");
    setFeedback(draft?.userFeedback ?? "");
    if (draft) {
      setGoal(draft.goal);
      setTone(draft.tone);
      setLanguage(draft.language);
    }
    setCopied("");
  }

  async function saveContact() {
    if (!contact || !form) return;
    if (form.status === "SENT" && contact.status !== "SENT" && !window.confirm(SENT_REMINDER)) return;
    setSaving(true);
    setError("");
    try {
      const updated = await apiJson<ContactDto>(`/api/contacts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          fullName: form.fullName,
          linkedinId: form.linkedinId,
          linkedinUrl: form.linkedinUrl,
          headline: form.headline,
          occupation: form.occupation,
          company: form.company,
          industry: form.industry,
          location: form.location,
          interests: linesToList(form.interestsText),
          notes: form.notes,
          status: form.status,
        }),
      });
      const next = { ...contact, ...updated };
      setContact(next);
      setForm(toForm(next));
      setEditing(false);
      setNotice("Контакт сохранён.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить контакт");
    } finally {
      setSaving(false);
    }
  }

  async function removeContact() {
    if (!window.confirm("Удалить контакт вместе с черновиками?")) return;
    try {
      await apiJson(`/api/contacts/${id}`, { method: "DELETE" });
      router.push("/contacts");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось удалить контакт");
    }
  }

  async function generate() {
    setGenerating(true);
    setError("");
    setNotice("");
    try {
      const result = await apiJson<{ draft: DraftDto; contact: ContactDto }>(`/api/contacts/${id}/generate-message`, {
        method: "POST",
        body: JSON.stringify({ goal, tone, language, extraContext: extra }),
      });
      setContact((current) =>
        current
          ? { ...current, ...result.contact, drafts: [result.draft, ...current.drafts.filter((item) => item.id !== result.draft.id)] }
          : current,
      );
      selectDraft(result.draft);
      setNotice("Черновик готов. Проверьте риски и только потом копируйте текст.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось подготовить черновик");
    } finally {
      setGenerating(false);
    }
  }

  async function saveDraft() {
    if (!active) return;
    setSaving(true);
    setError("");
    try {
      const saved = await apiJson<DraftDto>(`/api/messages/${active.id}`, {
        method: "PATCH",
        body: JSON.stringify({ generatedText: text, userFeedback: feedback, isApproved: true }),
      });
      setContact((current) =>
        current ? { ...current, drafts: current.drafts.map((item) => (item.id === saved.id ? saved : item)) } : current,
      );
      setActive(saved);
      setNotice("Черновик сохранён.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить черновик");
    } finally {
      setSaving(false);
    }
  }

  async function markSent() {
    if (!contact) return;
    setSaving(true);
    setError("");
    try {
      const updated = await apiJson<ContactDto>(`/api/contacts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "SENT" }),
      });
      setContact((current) => (current ? { ...current, ...updated } : current));
      setForm((current) => (current ? { ...current, status: "SENT" } : current));
      setConfirmSent(false);
      setNotice("Статус изменён на «Отправлено».");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось обновить статус");
    } finally {
      setSaving(false);
    }
  }

  async function copy(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const area = document.createElement("textarea");
      area.value = value;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setCopied(label);
  }

  if (missing) {
    return (
      <div className="card">
        <p>{error || "Контакт не найден"}</p>
        <Link className="mt-3 inline-block text-sm underline" href="/contacts">
          К списку
        </Link>
      </div>
    );
  }
  if (!contact || !form) return <p className="text-sm text-stone-500">Загрузка…</p>;

  const length = text.length;
  const lengthOk = length >= 350 && length <= 700;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{contact.fullName}</h1>
          <p className="mt-1 text-stone-600">
            {contact.headline || contact.occupation}
            {contact.company ? ` · ${contact.company}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge large status={contact.status} />
          <a className="btn-primary" href="#generate">
            Сгенерировать обращение
          </a>
          {contact.linkedinUrl ? (
            <a className="btn-secondary" href={contact.linkedinUrl} target="_blank" rel="noreferrer">
              Открыть профиль
            </a>
          ) : null}
        </div>
      </div>

      {notice ? <p className="text-sm text-emerald-800">{notice}</p> : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <section className="card">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Карточка</h2>
          <button className="btn-secondary" type="button" onClick={() => setEditing((value) => !value)}>
            {editing ? "Закрыть редактирование" : "Редактировать"}
          </button>
        </div>
        {editing ? (
          <div className="mt-4">
            <ContactForm
              values={form}
              onChange={setForm}
              onSubmit={() => void saveContact()}
              submitLabel="Сохранить контакт"
              pending={saving}
              error=""
              showStatus
            />
          </div>
        ) : (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <Info label="LinkedIn ID" value={contact.linkedinId} />
            <Info label="Род занятий" value={contact.occupation} />
            <Info label="Отрасль" value={contact.industry} />
            <Info label="Город" value={contact.location} />
            <Info label="Последняя отправка" value={formatDate(contact.lastContactedAt)} />
            <div className="sm:col-span-2">
              <dt className="text-stone-500">Интересы и задачи</dt>
              <dd className="mt-1">{contact.interests.length ? contact.interests.join(" · ") : "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-stone-500">Заметки</dt>
              <dd className="mt-1 whitespace-pre-wrap">{contact.notes || "—"}</dd>
            </div>
          </dl>
        )}
        <button className="btn-danger mt-4" type="button" onClick={() => void removeContact()}>
          Удалить контакт
        </button>
      </section>

      <section className="card" id="generate">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
          <div>
            <h2 className="text-lg font-semibold">Сгенерировать обращение</h2>
            <p className="mt-1 text-sm text-stone-600">
              Модель видит только карточку, заметки и ваш профиль. Факты она не достраивает, а сообщение никуда не
              отправляется.
            </p>
          </div>
          <Link className="text-sm underline" href="/profile">
            Мой профиль
          </Link>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="md:col-span-3">
            <span className="label">Цель обращения</span>
            <input className="field" value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Например, обсудить разбор цикла найма" />
          </label>
          <label>
            <span className="label">Тон</span>
            <select className="field" value={tone} onChange={(event) => setTone(event.target.value as MessageTone)}>
              {MESSAGE_TONES.map((item) => (
                <option key={item} value={item}>
                  {TONE_LABELS[item]}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">Язык</span>
            <select className="field" value={language} onChange={(event) => setLanguage(event.target.value)}>
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
          <label className="md:col-span-3">
            <span className="label">Дополнительный контекст</span>
            <textarea className="field min-h-20" value={extra} onChange={(event) => setExtra(event.target.value)} />
          </label>
        </div>
        <button className="btn-primary mt-3" type="button" disabled={generating || !goal.trim()} onClick={() => void generate()}>
          {generating ? "Готовлю вариант…" : active ? "Сгенерировать другой вариант" : "Сгенерировать обращение"}
        </button>

        {active ? (
          <div className="mt-5 space-y-3 border-t border-stone-200 pt-5">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span>
                Версия {active.version}
                {active.isApproved ? " · сохранён" : ""} · {TONE_LABELS[active.tone]}
              </span>
              <span className={lengthOk ? "text-emerald-800" : "text-amber-800"}>{length} символов</span>
            </div>
            <textarea className="field min-h-48" value={text} onChange={(event) => setText(event.target.value)} />
            <label>
              <span className="label">Заметка к черновику</span>
              <input className="field" value={feedback} onChange={(event) => setFeedback(event.target.value)} />
            </label>
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" onClick={() => void copy(text, "message")}>
                {copied === "message" ? "Скопировано" : "Скопировать текст"}
              </button>
              <button className="btn-secondary" type="button" disabled={generating || !goal.trim()} onClick={() => void generate()}>
                Сгенерировать другой вариант
              </button>
              <button className="btn-primary" type="button" disabled={saving} onClick={() => void saveDraft()}>
                Сохранить черновик
              </button>
              <button className="btn-secondary" type="button" onClick={() => setConfirmSent(true)}>
                Отметить как отправлено
              </button>
            </div>
            {confirmSent ? (
              <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
                <p className="font-medium">{SENT_REMINDER}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="btn-primary" type="button" disabled={saving} onClick={() => void markSent()}>
                    Да, я отправил вручную
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => setConfirmSent(false)}>
                    Отмена
                  </button>
                </div>
              </div>
            ) : null}
            <Hint title="Что использовано" items={active.personalizationHooks} />
            <Hint title="Что проверить" items={active.risks} />
            {active.suggestedFollowUp ? (
              <div className="rounded-xl bg-stone-50 p-3 text-sm">
                <div className="font-medium">Follow-up, если не ответят</div>
                <p className="mt-1 whitespace-pre-wrap">{active.suggestedFollowUp}</p>
                <button className="btn-secondary mt-2" type="button" onClick={() => void copy(active.suggestedFollowUp, "follow")}>
                  {copied === "follow" ? "Скопировано" : "Скопировать follow-up"}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="card">
        <h2 className="text-lg font-semibold">История черновиков</h2>
        {contact.drafts.length === 0 ? (
          <p className="mt-3 text-sm text-stone-500">Черновиков пока нет.</p>
        ) : (
          <ul className="mt-3 divide-y divide-stone-100">
            {contact.drafts.map((draft) => (
              <li key={draft.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium">
                    Версия {draft.version}
                    {draft.isApproved ? " · сохранён" : ""}
                  </div>
                  <div className="text-sm text-stone-500">
                    {draft.goal} · {TONE_LABELS[draft.tone]} · {formatDate(draft.createdAt)}
                  </div>
                </div>
                <button className="btn-secondary" type="button" onClick={() => selectDraft(draft)}>
                  Открыть
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function toForm(contact: ContactDto): ContactFormValues {
  return {
    fullName: contact.fullName,
    linkedinId: contact.linkedinId,
    linkedinUrl: contact.linkedinUrl ?? "",
    headline: contact.headline ?? "",
    occupation: contact.occupation,
    company: contact.company ?? "",
    industry: contact.industry ?? "",
    location: contact.location ?? "",
    interestsText: listToLines(contact.interests),
    notes: contact.notes ?? "",
    status: contact.status,
  };
}

function Info({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-stone-500">{label}</dt>
      <dd className="mt-1">{value || "—"}</dd>
    </div>
  );
}

function Hint({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <div className="text-sm font-medium">{title}</div>
      <ul className="mt-1 list-disc pl-5 text-sm text-stone-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
