"use client";

import { useState } from "react";

const SAMPLE = `fullName,linkedinId,linkedinUrl,headline,occupation,company,industry,location,interests,notes
"Ольга Виноградова",demo-olga-vinogradova,https://www.linkedin.com/in/demo-olga-vinogradova,"Руководитель клиентского сервиса","Клиентский сервис","Ясная","Услуги","Москва","удержание клиентов | скорость ответа","Познакомились на отраслевом завтраке"
`;

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ created: number; updated: number; skipped: number; errors: string[] } | null>(null);

  async function upload() {
    if (!file) {
      setError("Выберите CSV-файл");
      return;
    }
    setPending(true);
    setError("");
    setResult(null);
    try {
      const body = new FormData();
      body.set("file", file);
      const response = await fetch("/api/contacts/import", { method: "POST", body });
      const data = (await response.json()) as {
        error?: string;
        created: number;
        updated: number;
        skipped: number;
        errors: string[];
      };
      if (!response.ok) throw new Error(data.error || "Не удалось импортировать файл");
      setResult(data);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось импортировать файл");
    } finally {
      setPending(false);
    }
  }

  function downloadSample() {
    const blob = new Blob([`\uFEFF${SAMPLE}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "contacts-sample.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Импорт CSV</h1>
        <p className="mt-1 max-w-3xl text-sm text-stone-600">
          Загрузите Connections.csv из профиля, указанного в LINKEDIN_PROFILE_URL. На компьютере: значок профиля →
          «Настройки и конфиденциальность» → «Конфиденциальность данных» → «Загрузка своих данных» → отметьте «Контакты»
          → «Запросить архив». Ссылка придёт на почту. В ZIP нужен файл Connections.csv. Его можно загрузить здесь или
          указать путь в LINKEDIN_CONNECTIONS_CSV. Приложение само в LinkedIn не входит.
        </p>
      </div>
      <div className="card space-y-4">
        <input
          className="block text-sm"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" type="button" disabled={pending} onClick={() => void upload()}>
            {pending ? "Загрузка…" : "Импортировать"}
          </button>
          <button className="btn-secondary" type="button" onClick={downloadSample}>
            Скачать пример
          </button>
        </div>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {result ? (
          <div className="text-sm">
            <p>
              Добавлено: {result.created}. Обновлено: {result.updated}. Пропущено: {result.skipped}.
            </p>
            {result.errors.length > 0 ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-red-800">
                {result.errors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
