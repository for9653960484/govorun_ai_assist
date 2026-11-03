import { z } from "zod";
import { CONTACT_STATUSES, MESSAGE_TONES } from "@/lib/labels";

const optionalText = (max: number) =>
  z
    .union([z.string().trim().max(max, `Не длиннее ${max} символов`), z.literal(""), z.null()])
    .optional()
    .transform((value) => (value === undefined ? undefined : value ? value : null));

export const contactStatusSchema = z.enum(CONTACT_STATUSES);
export const messageToneSchema = z.enum(MESSAGE_TONES);

export const contactCreateSchema = z.object({
  fullName: z.string().trim().min(1, "Укажите ФИО").max(200),
  linkedinId: z
    .string()
    .trim()
    .min(1, "Укажите LinkedIn ID")
    .max(200)
    .transform((value) => normalizeLinkedinId(value))
    .refine((value) => /^[\p{L}\p{N}._-]+$/u.test(value), "LinkedIn ID содержит недопустимые символы"),
  linkedinUrl: optionalText(500),
  headline: optionalText(300),
  occupation: z.string().trim().min(1, "Укажите род занятий").max(300),
  company: optionalText(200),
  industry: optionalText(200),
  location: optionalText(200),
  interests: z.array(z.string().trim().min(1).max(300)).max(40).optional().default([]),
  notes: optionalText(5000),
  status: contactStatusSchema.optional(),
});

export const contactPatchSchema = z
  .object({
    fullName: z.string().trim().min(1, "Укажите ФИО").max(200).optional(),
    linkedinId: z
      .string()
      .trim()
      .min(1, "Укажите LinkedIn ID")
      .max(200)
      .transform((value) => normalizeLinkedinId(value))
      .refine((value) => /^[\p{L}\p{N}._-]+$/u.test(value), "LinkedIn ID содержит недопустимые символы")
      .optional(),
    linkedinUrl: optionalText(500),
    headline: optionalText(300),
    occupation: z.string().trim().min(1, "Укажите род занятий").max(300).optional(),
    company: optionalText(200),
    industry: optionalText(200),
    location: optionalText(200),
    interests: z.array(z.string().trim().min(1).max(300)).max(40).optional(),
    notes: optionalText(5000),
    status: contactStatusSchema.optional(),
  })
  .refine((value) => Object.values(value).some((item) => item !== undefined), {
    message: "Нет данных для сохранения",
  });

export const listQuerySchema = z.object({
  q: z.string().trim().max(200).optional(),
  status: z.union([contactStatusSchema, z.literal("")]).optional().transform((value) => value || undefined),
  industry: z.string().trim().max(200).optional().transform((value) => value || undefined),
  company: z.string().trim().max(200).optional().transform((value) => value || undefined),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(10),
});

export const generateMessageSchema = z.object({
  goal: z.string().trim().min(1, "Укажите цель обращения").max(500),
  tone: messageToneSchema,
  language: z.string().trim().min(2, "Укажите язык").max(12).default("ru"),
  extraContext: z.string().trim().max(2000).optional().or(z.literal("")).transform((value) => value || undefined),
});

export const messagePatchSchema = z
  .object({
    generatedText: z.string().trim().min(1, "Текст черновика пуст").max(5000).optional(),
    isApproved: z.boolean().optional(),
    userFeedback: optionalText(2000),
  })
  .refine((value) => Object.values(value).some((item) => item !== undefined), {
    message: "Нет данных для сохранения",
  });

export const profileSchema = z.object({
  name: z.string().trim().min(1, "Укажите имя").max(200),
  currentRole: z.string().trim().min(1, "Укажите текущую роль").max(300),
  company: optionalText(200),
  keyExperience: z.string().trim().min(1, "Опишите релевантный опыт").max(5000),
  achievements: z.array(z.string().trim().min(1).max(500)).max(30),
  valueProposition: z.string().trim().min(1, "Опишите, чем вы можете быть полезны").max(2000),
  preferredNextStep: z.string().trim().min(1, "Укажите желаемый следующий шаг").max(300),
});

export type ContactCreateInput = z.infer<typeof contactCreateSchema>;
export type ContactPatchInput = z.infer<typeof contactPatchSchema>;
export type ProfileInput = z.infer<typeof profileSchema>;

function normalizeLinkedinId(value: string): string {
  const trimmed = value.trim();
  if (!/^https?:\/\//i.test(trimmed)) return trimmed;
  try {
    const parts = new URL(trimmed).pathname.split("/").filter(Boolean);
    return decodeURIComponent(parts[parts.length - 1] ?? trimmed);
  } catch {
    return trimmed;
  }
}
