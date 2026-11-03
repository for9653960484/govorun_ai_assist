import fs from "fs";
import { prisma } from "@/lib/prisma";
import { dumpList } from "@/lib/text";
import { loadRootEnv } from "@/lib/rootEnv";
import { linkedInAccountFromEnv } from "@/lib/linkedin";
import { importContactsCsv, type ImportResult } from "@/lib/importContacts";

const DEMO_NAME = "Марина Волкова";
const PLACEHOLDER_ROLE = "Укажите текущую роль";

let connectionsStamp = "";

export type OwnerState = {
  name: string;
  linkedinUrl: string;
  connectionsFile: string;
  connectionsFound: boolean;
  importResult: ImportResult | null;
};

export async function ensureWorkspace(): Promise<OwnerState> {
  loadRootEnv();
  const account = linkedInAccountFromEnv();
  await prisma.contact.deleteMany({ where: { linkedinId: { startsWith: "demo-" } } });
  if (!account) {
    return { name: "", linkedinUrl: "", connectionsFile: "", connectionsFound: false, importResult: null };
  }
  await syncProfile(account.name, account.url);
  const connectionsFile = process.env.LINKEDIN_CONNECTIONS_CSV?.trim() ?? "";
  const importResult = await importConnectionsFile(connectionsFile);
  return {
    name: account.name,
    linkedinUrl: account.url,
    connectionsFile,
    connectionsFound: Boolean(connectionsFile && fs.existsSync(connectionsFile)),
    importResult,
  };
}

async function syncProfile(name: string, linkedinUrl: string) {
  const current = await prisma.userProfile.findFirst({ orderBy: { createdAt: "asc" } });
  if (!current || current.name === DEMO_NAME) {
    const data = {
      name,
      linkedinUrl,
      currentRole: current && current.name !== DEMO_NAME ? current.currentRole : PLACEHOLDER_ROLE,
      company: current?.name === DEMO_NAME ? null : (current?.company ?? null),
      keyExperience:
        current && current.name !== DEMO_NAME
          ? current.keyExperience
          : "Опишите опыт, который можно упоминать в обращении.",
      achievements: current && current.name !== DEMO_NAME ? current.achievements : dumpList([]),
      valueProposition:
        current && current.name !== DEMO_NAME
          ? current.valueProposition
          : "Опишите, чем вы можете быть полезны контакту.",
      preferredNextStep:
        current && current.name !== DEMO_NAME ? current.preferredNextStep : "короткий созвон на 15 минут",
    };
    if (current) await prisma.userProfile.update({ where: { id: current.id }, data });
    else await prisma.userProfile.create({ data });
    return;
  }
  if (current.linkedinUrl !== linkedinUrl) {
    await prisma.userProfile.update({ where: { id: current.id }, data: { linkedinUrl } });
  }
}

async function importConnectionsFile(file: string): Promise<ImportResult | null> {
  if (!file || !fs.existsSync(file)) return null;
  const stat = fs.statSync(file);
  const stamp = `${file}:${stat.mtimeMs}:${stat.size}`;
  if (stamp === connectionsStamp) return null;
  const text = fs.readFileSync(file, "utf8");
  const result = await importContactsCsv(text);
  connectionsStamp = stamp;
  return result;
}
