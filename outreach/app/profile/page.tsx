"use client";

import { useEffect, useState } from "react";
import { apiJson, type ProfileDto } from "@/lib/client";
import { linesToList, listToLines } from "@/lib/text";

type FormState = {
  name: string;
  currentRole: string;
  company: string;
  keyExperience: string;
  achievementsText: string;
  valueProposition: string;
  preferredNextStep: string;
  linkedinUrl: string;
};

const emptyForm: FormState = {
  name: "",
  currentRole: "",
  company: "",
  keyExperience: "",
  achievementsText: "",
  valueProposition: "",
  preferredNextStep: "",
  linkedinUrl: "",
};

export default function ProfilePage() {
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    void apiJson<{ profile: ProfileDto | null }>("/api/profile")
      .then((payload) => {
        if (!payload.profile) return;
        setForm({
          name: payload.profile.name,
          currentRole: payload.profile.currentRole,
          company: payload.profile.company ?? "",
          keyExperience: payload.profile.keyExperience,
          achievementsText: listToLines(payload.profile.achievements),
          valueProposition: payload.profile.valueProposition,
          preferredNextStep: payload.profile.preferredNextStep,
          linkedinUrl: payload.profile.linkedinUrl ?? "",
        });
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить профиль"));
  }, []);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    setPending(true);
    setError("");
    setNotice("");
    try {
      await apiJson<ProfileDto>("/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          name: form.name,
          currentRole: form.currentRole,
          company: form.company,
          keyExperience: form.keyExperience,
          achievements: linesToList(form.achievementsText),
          valueProposition: form.valueProposition,
          preferredNextStep: form.preferredNextStep,
        }),
      });
      setNotice("Профиль сохранён. Новые черновики будут опираться на эти данные.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить профиль");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Мой профиль</h1>
        <p className="mt-1 max-w-3xl text-sm text-stone-600">
          Эти сведения попадают в черновик как факты о вас. Профиль LinkedIn задаётся в корневом .env и сюда не
          подставляется из сайта LinkedIn.
        </p>
        {form.linkedinUrl ? (
          <a className="mt-2 inline-block text-sm underline" href={form.linkedinUrl} target="_blank" rel="noreferrer">
            {form.linkedinUrl}
          </a>
        ) : null}
      </div>
      <form
        className="card grid gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <label>
            <span className="label">Имя</span>
            <input className="field" value={form.name} onChange={(event) => set("name", event.target.value)} required />
          </label>
          <label>
            <span className="label">Текущая роль</span>
            <input className="field" value={form.currentRole} onChange={(event) => set("currentRole", event.target.value)} required />
          </label>
        </div>
        <label>
          <span className="label">Компания</span>
          <input className="field" value={form.company} onChange={(event) => set("company", event.target.value)} />
        </label>
        <label>
          <span className="label">Релевантный опыт</span>
          <textarea className="field min-h-28" value={form.keyExperience} onChange={(event) => set("keyExperience", event.target.value)} required />
        </label>
        <label>
          <span className="label">Достижения и кейсы</span>
          <textarea
            className="field min-h-28"
            value={form.achievementsText}
            onChange={(event) => set("achievementsText", event.target.value)}
            placeholder="Каждый кейс с новой строки"
          />
        </label>
        <label>
          <span className="label">Чем можете быть полезны</span>
          <textarea className="field min-h-24" value={form.valueProposition} onChange={(event) => set("valueProposition", event.target.value)} required />
        </label>
        <label>
          <span className="label">Предпочитаемый следующий шаг</span>
          <input className="field" value={form.preferredNextStep} onChange={(event) => set("preferredNextStep", event.target.value)} required />
        </label>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {notice ? <p className="text-sm text-emerald-800">{notice}</p> : null}
        <div>
          <button className="btn-primary" type="submit" disabled={pending}>
            {pending ? "Сохранение…" : "Сохранить профиль"}
          </button>
        </div>
      </form>
    </div>
  );
}
