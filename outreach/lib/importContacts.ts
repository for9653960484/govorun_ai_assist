import { createContactData, patchContactData } from "@/lib/contacts";
import { parseCsv, type CsvRow } from "@/lib/csv";
import { prisma } from "@/lib/prisma";
import { linkedinIdFromUrl, linkedInAccountFromEnv } from "@/lib/linkedin";
import { splitMulti } from "@/lib/text";
import { contactCreateSchema } from "@/lib/validators";

export type ImportResult = {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
};

export async function importContactsCsv(source: string): Promise<ImportResult> {
  const rows = parseCsv(source);
  if (rows.length === 0) {
    return { created: 0, updated: 0, skipped: 0, errors: ["В файле нет строк с контактами"] };
  }
  const header = Object.keys(rows[0]).map((name) => name.toLowerCase());
  const linkedInExport = header.includes("first name") && header.includes("url");
  const ownExport = header.includes("fullname") && header.includes("linkedinid");
  if (!linkedInExport && !ownExport) {
    return {
      created: 0,
      updated: 0,
      skipped: rows.length,
      errors: ["Нужен файл Connections.csv из LinkedIn или CSV с колонками fullName, linkedinId, occupation"],
    };
  }

  const ownerId = linkedInAccountFromEnv()?.linkedinId.toLowerCase() ?? "";
  const errors: string[] = [];
  const seen = new Set<string>();
  let created = 0;
  let updated = 0;

  for (const [index, row] of rows.entries()) {
    const line = index + 2;
    const mapped = linkedInExport ? fromLinkedInRow(row) : fromOwnRow(row);
    if (!mapped) {
      errors.push(`Строка ${line}: нет имени или ссылки на профиль`);
      continue;
    }
    if (ownerId && mapped.linkedinId.toLowerCase() === ownerId) continue;
    const parsed = contactCreateSchema.safeParse(mapped);
    if (!parsed.success) {
      errors.push(`Строка ${line}: ${parsed.error.issues.map((issue) => issue.message).join("; ")}`);
      continue;
    }
    if (seen.has(parsed.data.linkedinId)) {
      errors.push(`Строка ${line}: LinkedIn ID повторяется в файле`);
      continue;
    }
    seen.add(parsed.data.linkedinId);
    try {
      const existing = await prisma.contact.findUnique({ where: { linkedinId: parsed.data.linkedinId } });
      if (!existing) {
        await prisma.contact.create({ data: createContactData(parsed.data) });
        created += 1;
        continue;
      }
      await prisma.contact.update({
        where: { id: existing.id },
        data: patchContactData(existing, {
          fullName: parsed.data.fullName,
          linkedinUrl: parsed.data.linkedinUrl,
          headline: parsed.data.headline,
          occupation: parsed.data.occupation,
          company: parsed.data.company,
          ...(existing.notes ? {} : { notes: parsed.data.notes }),
        }),
      });
      updated += 1;
    } catch {
      errors.push(`Строка ${line}: не удалось сохранить`);
    }
  }

  return { created, updated, skipped: rows.length - created - updated, errors };
}

function fromOwnRow(row: CsvRow) {
  return {
    fullName: cell(row, "fullName"),
    linkedinId: cell(row, "linkedinId"),
    linkedinUrl: cell(row, "linkedinUrl"),
    headline: cell(row, "headline"),
    occupation: cell(row, "occupation"),
    company: cell(row, "company"),
    industry: cell(row, "industry"),
    location: cell(row, "location"),
    interests: splitMulti(cell(row, "interests")),
    notes: cell(row, "notes"),
  };
}

function fromLinkedInRow(row: CsvRow) {
  const first = cell(row, "First Name");
  const last = cell(row, "Last Name");
  const url = cell(row, "URL");
  const linkedinId = linkedinIdFromUrl(url);
  const position = cell(row, "Position");
  const email = cell(row, "Email Address");
  const connected = cell(row, "Connected On");
  const notes = [
    email ? `Email: ${email}` : "",
    connected ? `В контактах с ${connected}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  if (!linkedinId || !(first || last)) return null;
  return {
    fullName: [first, last].filter(Boolean).join(" "),
    linkedinId,
    linkedinUrl: url,
    headline: position,
    occupation: position || "Контакт LinkedIn",
    company: cell(row, "Company"),
    industry: "",
    location: "",
    interests: [] as string[],
    notes,
  };
}

function cell(row: CsvRow, name: string): string {
  const found = Object.entries(row).find(([key]) => key.toLowerCase() === name.toLowerCase());
  return found?.[1]?.trim() ?? "";
}
