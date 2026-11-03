"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { apiJson, type ContactDto } from "@/lib/client";
import { CONTACT_STATUSES, STATUS_LABELS, formatDate, type ContactStatus } from "@/lib/labels";

type ListResponse = {
  items: ContactDto[];
  total: number;
  page: number;
  pageSize: number;
  owner?: { name: string; linkedinUrl: string; connectionsFound: boolean };
};

export function ContactsScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState("");
  const [pendingId, setPendingId] = useState("");
  const [draftQuery, setDraftQuery] = useState({
    q: searchParams.get("q") ?? "",
    industry: searchParams.get("industry") ?? "",
    company: searchParams.get("company") ?? "",
  });

  useEffect(() => {
    setDraftQuery({
      q: searchParams.get("q") ?? "",
      industry: searchParams.get("industry") ?? "",
      company: searchParams.get("company") ?? "",
    });
    const params = searchParams.toString();
    void apiJson<ListResponse>(`/api/contacts${params ? `?${params}` : ""}`)
      .then((payload) => {
        setData(payload);
        setError("");
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить контакты"));
  }, [searchParams]);

  function apply(next: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    if (!("page" in next)) params.delete("page");
    const query = params.toString();
    router.push(query ? `/contacts?${query}` : "/contacts");
  }

  async function changeStatus(contact: ContactDto, status: ContactStatus) {
    if (status === "SENT" && contact.status !== "SENT") {
      const confirmed = window.confirm("Убедитесь, что вы отправили сообщение вручную в LinkedIn.");
      if (!confirmed) return;
    }
    setPendingId(contact.id);
    setError("");
    try {
      const updated = await apiJson<ContactDto>(`/api/contacts/${contact.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setData((current) =>
        current
          ? { ...current, items: current.items.map((item) => (item.id === contact.id ? updated : item)) }
          : current,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сменить статус");
    } finally {
      setPendingId("");
    }
  }

  const page = Number(searchParams.get("page") ?? data?.page ?? 1);
  const pageSize = data?.pageSize ?? 10;
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold">Контакты</h1>
          <p className="mt-1 text-sm text-stone-600">
            {data?.owner?.linkedinUrl
              ? `Сеть профиля ${data.owner.name}.`
              : "Профиль LinkedIn не задан в корневом .env."}{" "}
            Поиск по имени, компании, должности и LinkedIn ID.
          </p>
          {data?.owner?.linkedinUrl && !data.owner.connectionsFound && data.total === 0 ? (
            <p className="mt-2 max-w-2xl text-sm text-stone-600">
              Список контактов берётся из выгрузки этого профиля. На компьютере откройте LinkedIn, значок профиля,
              «Настройки и конфиденциальность», слева «Конфиденциальность данных», затем «Загрузка своих данных».
              Отметьте «Контакты» и нажмите «Запросить архив». В письме будет ссылка на ZIP, внутри файл Connections.csv.
              Укажите путь к нему в LINKEDIN_CONNECTIONS_CSV или загрузите его на странице «Импорт».
            </p>
          ) : null}
        </div>
        <div className="flex gap-2">
          <a className="btn-secondary" href="/api/contacts/export">
            Экспорт CSV
          </a>
          <Link className="btn-primary" href="/contacts/new">
            Добавить
          </Link>
        </div>
      </div>

      <form
        className="card grid gap-3 md:grid-cols-4"
        onSubmit={(event) => {
          event.preventDefault();
          apply({ q: draftQuery.q.trim(), industry: draftQuery.industry.trim(), company: draftQuery.company.trim() });
        }}
      >
        <label className="md:col-span-2">
          <span className="label">Поиск</span>
          <input className="field" value={draftQuery.q} onChange={(event) => setDraftQuery({ ...draftQuery, q: event.target.value })} />
        </label>
        <label>
          <span className="label">Статус</span>
          <select
            className="field"
            value={searchParams.get("status") ?? ""}
            onChange={(event) => apply({ status: event.target.value, q: draftQuery.q, industry: draftQuery.industry, company: draftQuery.company })}
          >
            <option value="">Все</option>
            {CONTACT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">Отрасль</span>
          <input className="field" value={draftQuery.industry} onChange={(event) => setDraftQuery({ ...draftQuery, industry: event.target.value })} />
        </label>
        <label>
          <span className="label">Компания</span>
          <input className="field" value={draftQuery.company} onChange={(event) => setDraftQuery({ ...draftQuery, company: event.target.value })} />
        </label>
        <div className="flex items-end">
          <button className="btn-primary" type="submit">
            Найти
          </button>
        </div>
      </form>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <div className="card overflow-x-auto p-0">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-stone-200 text-stone-500">
            <tr>
              <th className="px-4 py-3 font-medium">Контакт</th>
              <th className="px-4 py-3 font-medium">Компания</th>
              <th className="px-4 py-3 font-medium">Отрасль</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Обновлён</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.length ? (
              data.items.map((contact) => (
                <tr key={contact.id} className="border-b border-stone-100 align-top">
                  <td className="px-4 py-3">
                    <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline">
                      {contact.fullName}
                    </Link>
                    <div className="text-stone-500">{contact.headline || contact.occupation}</div>
                    <div className="text-xs text-stone-400">{contact.linkedinId}</div>
                  </td>
                  <td className="px-4 py-3">{contact.company || "—"}</td>
                  <td className="px-4 py-3">{contact.industry || "—"}</td>
                  <td className="px-4 py-3">
                    <label className="sr-only" htmlFor={`status-${contact.id}`}>
                      Статус {contact.fullName}
                    </label>
                    <select
                      id={`status-${contact.id}`}
                      className="field min-w-40"
                      value={contact.status}
                      disabled={pendingId === contact.id}
                      onChange={(event) => void changeStatus(contact, event.target.value as ContactStatus)}
                    >
                      {CONTACT_STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {STATUS_LABELS[status]}
                        </option>
                      ))}
                    </select>
                    <div className="mt-2">
                      <StatusBadge status={contact.status} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-stone-500">{formatDate(contact.updatedAt)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-8 text-stone-500" colSpan={5}>
                  {error ? "Не удалось показать список." : data ? "Ничего не найдено." : "Загрузка…"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {total > pageSize ? (
        <div className="flex items-center justify-between text-sm">
          <span className="text-stone-500">
            {total} всего, страница {page} из {pages}
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary" type="button" disabled={page <= 1} onClick={() => apply({ page: String(page - 1) })}>
              Назад
            </button>
            <button className="btn-secondary" type="button" disabled={page >= pages} onClick={() => apply({ page: String(page + 1) })}>
              Дальше
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
