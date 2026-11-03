import type { ContactStatus, MessageTone } from "@/lib/labels";

export type ContactDto = {
  id: string;
  fullName: string;
  linkedinId: string;
  linkedinUrl: string | null;
  headline: string | null;
  occupation: string;
  company: string | null;
  industry: string | null;
  location: string | null;
  interests: string[];
  notes: string | null;
  status: ContactStatus;
  lastContactedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type DraftDto = {
  id: string;
  contactId: string;
  goal: string;
  tone: MessageTone;
  language: string;
  generatedText: string;
  personalizationHooks: string[];
  risks: string[];
  suggestedFollowUp: string;
  version: number;
  isApproved: boolean;
  userFeedback: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ContactDetails = ContactDto & { drafts: DraftDto[] };

export type ProfileDto = {
  id: string;
  name: string;
  currentRole: string;
  company: string | null;
  keyExperience: string;
  achievements: string[];
  valueProposition: string;
  preferredNextStep: string;
  linkedinUrl: string | null;
  createdAt: string;
  updatedAt: string;
};

export async function apiJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(url, { ...init, headers });
  const text = await response.text();
  const data = text ? (JSON.parse(text) as { error?: string }) : {};
  if (!response.ok) throw new Error(data.error || "Не удалось выполнить запрос");
  return data as T;
}
