export const CONTACT_STATUSES = [
  "NEW",
  "RESEARCHED",
  "DRAFT_READY",
  "SENT",
  "REPLIED",
  "FOLLOW_UP_NEEDED",
  "CLOSED",
] as const;

export type ContactStatus = (typeof CONTACT_STATUSES)[number];

export const MESSAGE_TONES = ["PROFESSIONAL", "FRIENDLY", "DIRECT", "EXECUTIVE"] as const;

export type MessageTone = (typeof MESSAGE_TONES)[number];

export const STATUS_LABELS: Record<ContactStatus, string> = {
  NEW: "Новый",
  RESEARCHED: "Изучен",
  DRAFT_READY: "Черновик готов",
  SENT: "Отправлено",
  REPLIED: "Есть ответ",
  FOLLOW_UP_NEEDED: "Нужен follow-up",
  CLOSED: "Закрыт",
};

export const STATUS_STYLES: Record<ContactStatus, string> = {
  NEW: "bg-stone-100 text-stone-700",
  RESEARCHED: "bg-sky-50 text-sky-900",
  DRAFT_READY: "bg-amber-50 text-amber-950",
  SENT: "bg-emerald-50 text-emerald-950",
  REPLIED: "bg-teal-50 text-teal-950",
  FOLLOW_UP_NEEDED: "bg-orange-50 text-orange-950",
  CLOSED: "bg-stone-200 text-stone-600",
};

export const TONE_LABELS: Record<MessageTone, string> = {
  PROFESSIONAL: "Деловой",
  FRIENDLY: "Дружелюбный",
  DIRECT: "Прямой",
  EXECUTIVE: "Для руководителя",
};

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
