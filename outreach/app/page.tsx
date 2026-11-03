import Link from "next/link";
import { StatusBadge } from "@/components/StatusBadge";
import { prisma } from "@/lib/prisma";
import { CONTACT_STATUSES, STATUS_LABELS, formatDate } from "@/lib/labels";
import { ensureWorkspace } from "@/lib/workspace";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  await ensureWorkspace();
  const [grouped, followUps, recent, total] = await Promise.all([
    prisma.contact.groupBy({ by: ["status"], _count: { _all: true } }),
    prisma.contact.findMany({ where: { status: "FOLLOW_UP_NEEDED" }, orderBy: { updatedAt: "desc" }, take: 6 }),
    prisma.contact.findMany({ orderBy: { updatedAt: "desc" }, take: 6 }),
    prisma.contact.count(),
  ]);
  const counts = new Map(grouped.map((row) => [row.status, row._count._all]));

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold">Обзор</h1>
          <p className="mt-1 text-sm text-stone-600">
            {total === 0 ? "Контактов пока нет." : `В базе ${total} ${plural(total)}.`} Черновик готовится здесь,
            сообщение вы отправляете сами.
          </p>
        </div>
        <Link href="/contacts/new" className="btn-primary">
          Добавить контакт
        </Link>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {CONTACT_STATUSES.map((status) => (
          <Link key={status} href={`/contacts?status=${status}`} className="card block hover:border-emerald-900">
            <div className="text-sm text-stone-500">{STATUS_LABELS[status]}</div>
            <div className="mt-2 text-3xl font-semibold">{counts.get(status) ?? 0}</div>
          </Link>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="card">
          <h2 className="text-lg font-semibold">Нужен follow-up</h2>
          {followUps.length === 0 ? (
            <p className="mt-3 text-sm text-stone-500">Таких контактов нет.</p>
          ) : (
            <ul className="mt-3 divide-y divide-stone-100">
              {followUps.map((contact) => (
                <li key={contact.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline">
                      {contact.fullName}
                    </Link>
                    <div className="text-sm text-stone-500">{contact.company || contact.occupation}</div>
                  </div>
                  <span className="text-xs text-stone-400">{formatDate(contact.updatedAt)}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="card">
          <h2 className="text-lg font-semibold">Последние изменения</h2>
          {recent.length === 0 ? (
            <p className="mt-3 text-sm text-stone-500">История появится после первого контакта.</p>
          ) : (
            <ul className="mt-3 divide-y divide-stone-100">
              {recent.map((contact) => (
                <li key={contact.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline">
                      {contact.fullName}
                    </Link>
                    <div className="mt-1">
                      <StatusBadge status={contact.status} />
                    </div>
                  </div>
                  <span className="text-xs text-stone-400">{formatDate(contact.updatedAt)}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </div>
  );
}

function plural(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "контакт";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "контакта";
  return "контактов";
}
