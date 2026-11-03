import { NextResponse } from "next/server";
import { toCsv } from "@/lib/csv";
import { prisma } from "@/lib/prisma";
import { parseList } from "@/lib/text";

export const dynamic = "force-dynamic";

const HEADERS = [
  "fullName",
  "linkedinId",
  "linkedinUrl",
  "headline",
  "occupation",
  "company",
  "industry",
  "location",
  "interests",
  "notes",
  "status",
  "lastContactedAt",
];

export async function GET() {
  const contacts = await prisma.contact.findMany({ orderBy: { fullName: "asc" } });
  const rows = contacts.map((contact) => [
    contact.fullName,
    contact.linkedinId,
    contact.linkedinUrl ?? "",
    contact.headline ?? "",
    contact.occupation,
    contact.company ?? "",
    contact.industry ?? "",
    contact.location ?? "",
    parseList(contact.interests).join(" | "),
    contact.notes ?? "",
    contact.status,
    contact.lastContactedAt?.toISOString() ?? "",
  ]);
  const body = toCsv(HEADERS, rows);
  return new NextResponse(body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="contacts.csv"',
    },
  });
}
