import { PrismaClient } from "@prisma/client";
import { ensureWorkspace } from "../lib/workspace";

const prisma = new PrismaClient();

async function main() {
  const owner = await ensureWorkspace();
  if (!owner.linkedinUrl) {
    console.log("В корневом .env нет LINKEDIN_PROFILE_URL. Профиль не обновлён.");
    return;
  }
  const contacts = await prisma.contact.count();
  console.log(`Профиль: ${owner.name}. Контактов в базе: ${contacts}.`);
  if (!owner.connectionsFound) {
    console.log("Файл Connections.csv не указан. Положите путь в LINKEDIN_CONNECTIONS_CSV или загрузите файл на странице «Импорт».");
  }
}

main()
  .catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
