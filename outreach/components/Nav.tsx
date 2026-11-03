"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Обзор" },
  { href: "/contacts", label: "Контакты" },
  { href: "/contacts/new", label: "Новый контакт" },
  { href: "/contacts/import", label: "Импорт" },
  { href: "/profile", label: "Мой профиль" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-stone-200 bg-white/90">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="leading-tight">
          <span className="block text-base font-semibold">Outreach Assistant</span>
          <span className="block text-xs text-stone-500">Черновики для ручной отправки</span>
        </Link>
        <nav className="flex flex-wrap gap-1">
          {LINKS.map((link) => {
            const active = isActive(link.href, pathname);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-2 text-sm ${active ? "bg-emerald-950 text-white" : "text-stone-700 hover:bg-stone-100"}`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

function isActive(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/contacts") return pathname === "/contacts" || /^\/contacts\/(?!new$|import$)[^/]+/.test(pathname);
  return pathname === href;
}
