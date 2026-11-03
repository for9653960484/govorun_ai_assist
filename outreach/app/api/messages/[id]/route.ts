import { NextResponse } from "next/server";
import { toDraft } from "@/lib/contacts";
import { errorJson } from "@/lib/http";
import { prisma } from "@/lib/prisma";
import { messagePatchSchema } from "@/lib/validators";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, context: Context) {
  try {
    const { id } = await context.params;
    const current = await prisma.messageDraft.findUnique({ where: { id } });
    if (!current) return NextResponse.json({ error: "Черновик не найден" }, { status: 404 });
    const body: unknown = await request.json();
    const input = messagePatchSchema.parse(body);
    const updated = await prisma.messageDraft.update({
      where: { id },
      data: {
        ...(input.generatedText !== undefined ? { generatedText: input.generatedText } : {}),
        ...(input.isApproved !== undefined ? { isApproved: input.isApproved } : {}),
        ...(input.userFeedback !== undefined ? { userFeedback: input.userFeedback } : {}),
      },
    });
    return NextResponse.json(toDraft(updated));
  } catch (error) {
    return errorJson(error);
  }
}
