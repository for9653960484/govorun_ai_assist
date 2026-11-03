import { NextResponse } from "next/server";
import { toContact, toDraft } from "@/lib/contacts";
import { dumpList, parseList } from "@/lib/text";
import { generateOutreach } from "@/lib/ai/generateOutreach";
import { errorJson } from "@/lib/http";
import { prisma } from "@/lib/prisma";
import { generateMessageSchema } from "@/lib/validators";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ id: string }> };

const DRAFT_STATUSES = new Set(["NEW", "RESEARCHED"]);

export async function POST(request: Request, context: Context) {
  try {
    const { id } = await context.params;
    const contact = await prisma.contact.findUnique({ where: { id } });
    if (!contact) return NextResponse.json({ error: "Контакт не найден" }, { status: 404 });
    const profile = await prisma.userProfile.findFirst({ orderBy: { createdAt: "asc" } });
    if (!profile) {
      return NextResponse.json(
        { error: "Сначала заполните «Мой профиль»: для черновика нужны ваш опыт и следующий шаг." },
        { status: 400 },
      );
    }
    const body: unknown = await request.json();
    const input = generateMessageSchema.parse(body);
    const generated = await generateOutreach({
      goal: input.goal,
      tone: input.tone,
      language: input.language,
      extraContext: input.extraContext,
      contact: {
        fullName: contact.fullName,
        headline: contact.headline,
        occupation: contact.occupation,
        company: contact.company,
        industry: contact.industry,
        location: contact.location,
        interests: parseList(contact.interests),
        notes: contact.notes,
      },
      profile: {
        name: profile.name,
        currentRole: profile.currentRole,
        company: profile.company,
        keyExperience: profile.keyExperience,
        achievements: parseList(profile.achievements),
        valueProposition: profile.valueProposition,
        preferredNextStep: profile.preferredNextStep,
      },
    });

    const aggregate = await prisma.messageDraft.aggregate({
      where: { contactId: id },
      _max: { version: true },
    });
    const draft = await prisma.messageDraft.create({
      data: {
        contactId: id,
        goal: input.goal,
        tone: input.tone,
        language: input.language,
        generatedText: generated.message,
        personalizationHooks: dumpList(generated.personalizationHooks),
        risks: dumpList(generated.risks),
        suggestedFollowUp: generated.suggestedFollowUp,
        version: (aggregate._max.version ?? 0) + 1,
      },
    });
    const updated = DRAFT_STATUSES.has(contact.status)
      ? await prisma.contact.update({ where: { id }, data: { status: "DRAFT_READY" } })
      : contact;

    return NextResponse.json({ draft: toDraft(draft), contact: toContact(updated) }, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Сервис генерации")) {
      return NextResponse.json({ error: error.message }, { status: 502 });
    }
    return errorJson(error);
  }
}
