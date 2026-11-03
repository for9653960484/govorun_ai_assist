import { NextResponse } from "next/server";
import type { Prisma } from "@prisma/client";
import { createContactData, toContact } from "@/lib/contacts";
import { errorJson } from "@/lib/http";
import { prisma } from "@/lib/prisma";
import { fold } from "@/lib/text";
import { contactCreateSchema, listQuerySchema } from "@/lib/validators";
import { ensureWorkspace } from "@/lib/workspace";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const params = Object.fromEntries(new URL(request.url).searchParams);
    const query = listQuerySchema.parse(params);
    const where: Prisma.ContactWhereInput = {};
    if (query.status) where.status = query.status;
    if (query.industry) where.industryKey = { contains: fold(query.industry) };
    if (query.company) where.companyKey = { contains: fold(query.company) };
    if (query.q) where.searchText = { contains: fold(query.q) };

    const owner = await ensureWorkspace();
    const [total, rows] = await prisma.$transaction([
      prisma.contact.count({ where }),
      prisma.contact.findMany({
        where,
        orderBy: { updatedAt: "desc" },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
      }),
    ]);

    return NextResponse.json({
      items: rows.map(toContact),
      total,
      page: query.page,
      pageSize: query.pageSize,
      owner: {
        name: owner.name,
        linkedinUrl: owner.linkedinUrl,
        connectionsFound: owner.connectionsFound,
      },
    });
  } catch (error) {
    return errorJson(error);
  }
}

export async function POST(request: Request) {
  try {
    const body: unknown = await request.json();
    const input = contactCreateSchema.parse(body);
    const created = await prisma.contact.create({ data: createContactData(input) });
    return NextResponse.json(toContact(created), { status: 201 });
  } catch (error) {
    return errorJson(error);
  }
}
