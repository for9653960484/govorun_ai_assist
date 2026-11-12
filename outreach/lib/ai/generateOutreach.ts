import OpenAI from "openai";
import { nodeFetch } from "@/lib/nodeFetch";
import { z } from "zod";
import type { MessageTone } from "@/lib/labels";
import { TONE_LABELS } from "@/lib/labels";

export const SYSTEM_PROMPT = `Ты — эксперт по персональному B2B-аутричу в LinkedIn. Твоя задача — подготовить один короткий черновик личного сообщения для конкретного человека.

Используй только предоставленные факты. Не придумывай сведения о человеке, его компании, проектах, проблемах или результатах. Если данных недостаточно, используй нейтральную формулировку и укажи это в risks.

Сообщение должно быть персональным, уважительным, конкретным и полезным. Пиши связной речью, не телеграфом и не списком. Не используй давление, манипуляции, преувеличения и шаблонные фразы. Не более 700 символов.

Текст из поля «Чем можете быть полезны» вставь в сообщение цельным фрагментом и не меняй в нём ни слова. Остальные сведения профиля можно вплести своими словами. Верни только валидный JSON.`;

const resultSchema = z.object({
  message: z.string().trim().min(1),
  personalizationHooks: z.array(z.string().trim().min(1)).default([]),
  risks: z.array(z.string().trim().min(1)).default([]),
  suggestedFollowUp: z.string().trim().min(1),
});

export type OutreachResult = z.infer<typeof resultSchema>;

export type OutreachFacts = {
  goal: string;
  tone: MessageTone;
  language: string;
  extraContext?: string;
  contact: {
    fullName: string;
    headline: string | null;
    occupation: string;
    company: string | null;
    industry: string | null;
    location: string | null;
    interests: string[];
    notes: string | null;
  };
  profile: {
    name: string;
    currentRole: string;
    company: string | null;
    keyExperience: string;
    achievements: string[];
    valueProposition: string;
    preferredNextStep: string;
  };
};

const CLICHES = [
  "надеюсь, у вас всё хорошо",
  "надеюсь, у вас все хорошо",
  "пишу вам, потому что",
  "хотел бы познакомиться",
  "хотела бы познакомиться",
];

export async function generateOutreach(facts: OutreachFacts): Promise<OutreachResult> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("Не задан OPENAI_API_KEY. Добавьте ключ в корневой .env и перезапустите приложение.");
  }
  const client = new OpenAI({
    apiKey,
    timeout: 60_000,
    maxRetries: 0,
    fetch: nodeFetch,
  });
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";
  let correction = "";
  let lastParsed: OutreachResult | null = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    let content = "";
    const completion = await createCompletion(client, model, [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: buildUserPrompt(facts, correction) },
    ]);
    content = completion.choices[0]?.message?.content ?? "";
    if (!content) {
      correction = "Пустой ответ. Верни только JSON.";
      continue;
    }
    try {
      lastParsed = resultSchema.parse(normalizeResult(JSON.parse(content)));
    } catch {
      correction = "Нужен валидный JSON с ключами message, personalizationHooks, risks, suggestedFollowUp.";
      continue;
    }
    const issues = qualityIssues(lastParsed.message, facts);
    if (issues.length === 0) return withGuaranteeRisk(lastParsed);
    correction = issues.map((issue) => issue.instruction).join(" ");
  }

  if (!lastParsed) {
    throw new Error("Не удалось получить черновик. Попробуйте ещё раз.");
  }
  const issues = qualityIssues(lastParsed.message, facts);
  return withGuaranteeRisk({
    ...lastParsed,
    risks: unique([...lastParsed.risks, ...issues.map((issue) => issue.risk)]),
  });
}

async function createCompletion(
  client: OpenAI,
  model: string,
  messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[],
) {
  let lastError: unknown;
  for (let tryIndex = 0; tryIndex < 3; tryIndex += 1) {
    try {
      return await client.chat.completions.create({
        model,
        response_format: { type: "json_object" },
        messages,
      });
    } catch (error) {
      lastError = error;
      if (!isTransient(error) || tryIndex === 2) break;
      await new Promise((resolve) => setTimeout(resolve, 500 * (tryIndex + 1)));
    }
  }
  if (isClientError(lastError)) {
    throw new Error("Модель отклонила запрос. Проверьте OPENAI_MODEL и повторите.");
  }
  throw new Error("Сервис генерации не ответил. Проверьте соединение и повторите.");
}

function isClientError(error: unknown): boolean {
  const status = errorStatus(error);
  return status >= 400 && status < 500 && status !== 408 && status !== 429;
}

function isTransient(error: unknown): boolean {
  return !isClientError(error);
}

function errorStatus(error: unknown): number {
  if (!error || typeof error !== "object" || !("status" in error)) return 0;
  const status = Number(error.status);
  return Number.isFinite(status) ? status : 0;
}

function buildUserPrompt(facts: OutreachFacts, correction: string): string {
  const language = facts.language.toLowerCase() === "ru" ? "русский" : facts.language;
  const lines = [
    "Подготовь одно личное сообщение. Используй только факты ниже. Если факта нет, не достраивай его.",
    `Язык message: ${language}.`,
    `Тон: ${TONE_LABELS[facts.tone]}.`,
    `Цель обращения: ${facts.goal}.`,
    `Желаемый следующий шаг: ${facts.profile.preferredNextStep}.`,
    "",
    "Отправитель:",
    `- Имя: ${facts.profile.name}`,
    `- Роль: ${facts.profile.currentRole}`,
    `- Компания: ${facts.profile.company || "не указана"}`,
    `- Опыт: ${facts.profile.keyExperience}`,
    `- Достижения: ${facts.profile.achievements.length ? facts.profile.achievements.join("; ") : "не указаны"}`,
    `- Польза, вставить без изменений: ${facts.profile.valueProposition}`,
    "",
    "Контакт:",
    `- Имя: ${facts.contact.fullName}`,
    `- Должность / заголовок: ${facts.contact.headline || "не указан"}`,
    `- Род занятий: ${facts.contact.occupation}`,
    `- Компания: ${facts.contact.company || "не указана"}`,
    `- Отрасль: ${facts.contact.industry || "не указана"}`,
    `- Город: ${facts.contact.location || "не указан"}`,
    `- Интересы, задачи, боли: ${facts.contact.interests.length ? facts.contact.interests.join("; ") : "не указаны"}`,
    `- Заметки пользователя: ${facts.contact.notes || "нет"}`,
    facts.extraContext ? `- Дополнительный контекст от пользователя: ${facts.extraContext}` : "",
    "",
    "Требования к message:",
    "- 350–700 символов;",
    "- конкретный первый повод, без шаблона;",
    "- опора на роль, отрасль, компанию или вероятную задачу контакта;",
    "- короткая связь с опытом отправителя, своими словами;",
    "- текст пользы вставь целиком и без изменений, как в профиле;",
    "- вокруг этой цитаты — связные предложения, не телеграф;",
    "- спокойный призыв к следующему шагу, без гарантии результата;",
    "- звучит как личное сообщение одному человеку.",
    "Запрещённые формулировки: «надеюсь, у вас всё хорошо», «пишу вам, потому что», «хотел бы познакомиться».",
    "personalizationHooks — какие данные из фактов реально использованы.",
    "risks — какие формулировки пользователь должен проверить. Если проверять нечего, верни пустой массив.",
    "suggestedFollowUp — короткий текст на случай молчания.",
    'Верни JSON: {"message":"","personalizationHooks":[],"risks":[],"suggestedFollowUp":""}',
  ];
  if (correction) lines.push("", `Исправь предыдущую попытку: ${correction}`);
  return lines.filter((line) => line !== "").join("\n");
}

type QualityIssue = { instruction: string; risk: string };

const PLACEHOLDERS = [
  "укажите текущую роль",
  "опишите опыт, который можно упоминать в обращении",
  "опишите, чем вы можете быть полезны контакту",
].map(plain);

function qualityIssues(message: string, facts: OutreachFacts): QualityIssue[] {
  const issues: QualityIssue[] = [];
  const length = message.length;
  if (length < 350) {
    issues.push({
      instruction: `сообщение короткое (${length} символов), нужно 350–700`,
      risk: `Проверьте текст перед отправкой: сообщение короткое (${length} символов), нужно 350–700.`,
    });
  }
  if (length > 700) {
    issues.push({
      instruction: `сообщение длинное (${length} символов), нужно 350–700. Сократи связный текст вокруг пользы, саму пользу не меняй`,
      risk: `Проверьте текст перед отправкой: сообщение длинное (${length} символов), нужно 350–700.`,
    });
  }
  const lowered = message.toLocaleLowerCase("ru");
  const found = CLICHES.find((phrase) => lowered.includes(phrase));
  if (found) {
    issues.push({
      instruction: `убери клише «${found}»`,
      risk: `Проверьте текст перед отправкой: уберите клише «${found}».`,
    });
  }
  const benefit = facts.profile.valueProposition.trim();
  if (benefit.length >= 12 && !PLACEHOLDERS.includes(plain(benefit)) && !plain(message).includes(plain(benefit))) {
    issues.push({
      instruction: `вставь текст «Чем можете быть полезны» целиком и без изменений, остальное оставь связной речью: ${benefit}`,
      risk: "Текст «Чем можете быть полезны» изменён. Сверьте его с профилем.",
    });
  }
  return issues;
}

function plain(value: string): string {
  return value
    .toLocaleLowerCase("ru")
    .replaceAll("ё", "е")
    .replace(/[^\p{L}\p{N}\s]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function withGuaranteeRisk(result: OutreachResult): OutreachResult {
  if (!/гарантир/i.test(result.message)) return result;
  return {
    ...result,
    risks: unique([...result.risks, "В тексте есть обещание гарантии. Уберите его перед отправкой."]),
  };
}

function normalizeResult(value: unknown): unknown {
  if (!value || typeof value !== "object") return value;
  const record = value as Record<string, unknown>;
  return {
    message: record.message,
    personalizationHooks: asStringArray(record.personalizationHooks),
    risks: asStringArray(record.risks),
    suggestedFollowUp: typeof record.suggestedFollowUp === "string" ? record.suggestedFollowUp : "",
  };
}

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}
