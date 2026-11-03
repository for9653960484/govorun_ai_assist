import { NextResponse } from "next/server";
import { toDraft } from "@/lib/contacts";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const contactId = new URL(request.url).searchParams.get("contactId")?.trim();
  if (!contactId) return NextResponse.json({ error: "Укажите contactId" }, { status: 400 });
  const contact = await prisma.contact.findUnique({ where: { id: contactId } });
  if (!contact) return NextResponse.json({ error: "Контакт не найден" }, { status: 404 });
  const drafts = await prisma.messageDraft.findMany({
    where: { contactId },
    orderBy: { version: "desc" },
  });
  return NextResponse.json({ items: drafts.map(toDraft) });
}
