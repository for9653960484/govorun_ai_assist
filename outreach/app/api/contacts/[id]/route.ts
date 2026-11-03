import { NextResponse } from "next/server";
import { patchContactData, toContact, toDraft } from "@/lib/contacts";
import { errorJson } from "@/lib/http";
import { prisma } from "@/lib/prisma";
import { contactPatchSchema } from "@/lib/validators";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ id: string }> };

export async function GET(_request: Request, context: Context) {
  const { id } = await context.params;
  const contact = await prisma.contact.findUnique({
    where: { id },
    include: { drafts: { orderBy: { version: "desc" } } },
  });
  if (!contact) return NextResponse.json({ error: "Контакт не найден" }, { status: 404 });
  const { drafts, ...row } = contact;
  return NextResponse.json({ ...toContact(row), drafts: drafts.map(toDraft) });
}

export async function PATCH(request: Request, context: Context) {
  try {
    const { id } = await context.params;
    const current = await prisma.contact.findUnique({ where: { id } });
    if (!current) return NextResponse.json({ error: "Контакт не найден" }, { status: 404 });
    const body: unknown = await request.json();
    const input = contactPatchSchema.parse(body);
    const updated = await prisma.contact.update({
      where: { id },
      data: patchContactData(current, input),
    });
    return NextResponse.json(toContact(updated));
  } catch (error) {
    return errorJson(error);
  }
}

export async function DELETE(_request: Request, context: Context) {
  try {
    const { id } = await context.params;
    await prisma.contact.delete({ where: { id } });
    return NextResponse.json({ ok: true });
  } catch (error) {
    if (typeof error === "object" && error !== null && "code" in error && error.code === "P2025") {
      return NextResponse.json({ error: "Контакт не найден" }, { status: 404 });
    }
    return errorJson(error, 500);
  }
}
