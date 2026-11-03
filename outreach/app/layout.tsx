import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "LinkedIn Outreach Assistant",
  description: "Черновики персональных обращений и мини-CRM. Сообщения в LinkedIn отправляются только вручную.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-paper text-ink antialiased">
        <Nav />
        <main className="mx-auto w-full max-w-6xl px-4 py-6">{children}</main>
        <footer className="mx-auto w-full max-w-6xl px-4 pb-8 text-sm text-stone-500">
          Приложение не отправляет сообщения и приглашения в LinkedIn. Текст копируется, а статус вы отмечаете после
          ручной отправки.
        </footer>
      </body>
    </html>
  );
}
