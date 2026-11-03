import { NextResponse } from "next/server";
import { toProfile } from "@/lib/contacts";
import { errorJson } from "@/lib/http";
import { prisma } from "@/lib/prisma";
import { dumpList } from "@/lib/text";
import { profileSchema } from "@/lib/validators";
import { ensureWorkspace } from "@/lib/workspace";

export const dynamic = "force-dynamic";

export async function GET() {
  await ensureWorkspace();
  const profile = await prisma.userProfile.findFirst({ orderBy: { createdAt: "asc" } });
  return NextResponse.json({ profile: profile ? toProfile(profile) : null });
}

export async function PUT(request: Request) {
  try {
    const body: unknown = await request.json();
    const input = profileSchema.parse(body);
    const data = {
      name: input.name,
      currentRole: input.currentRole,
      company: input.company ?? null,
      keyExperience: input.keyExperience,
      achievements: dumpList(input.achievements),
      valueProposition: input.valueProposition,
      preferredNextStep: input.preferredNextStep,
    };
    const current = await prisma.userProfile.findFirst({ orderBy: { createdAt: "asc" } });
    const saved = current
      ? await prisma.userProfile.update({ where: { id: current.id }, data })
      : await prisma.userProfile.create({ data });
    return NextResponse.json(toProfile(saved));
  } catch (error) {
    return errorJson(error);
  }
}
