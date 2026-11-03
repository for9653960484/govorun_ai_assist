import type { Contact, MessageDraft, Prisma, UserProfile } from "@prisma/client";
import type { ContactCreateInput, ContactPatchInput } from "@/lib/validators";
import { dumpList, fold, parseList } from "@/lib/text";

export function toContact(row: Contact) {
  return {
    id: row.id,
    fullName: row.fullName,
    linkedinId: row.linkedinId,
    linkedinUrl: row.linkedinUrl,
    headline: row.headline,
    occupation: row.occupation,
    company: row.company,
    industry: row.industry,
    location: row.location,
    interests: parseList(row.interests),
    notes: row.notes,
    status: row.status,
    lastContactedAt: row.lastContactedAt?.toISOString() ?? null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export function toDraft(row: MessageDraft) {
  return {
    id: row.id,
    contactId: row.contactId,
    goal: row.goal,
    tone: row.tone,
    language: row.language,
    generatedText: row.generatedText,
    personalizationHooks: parseList(row.personalizationHooks),
    risks: parseList(row.risks),
    suggestedFollowUp: row.suggestedFollowUp,
    version: row.version,
    isApproved: row.isApproved,
    userFeedback: row.userFeedback,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export function toProfile(row: UserProfile) {
  return {
    id: row.id,
    name: row.name,
    currentRole: row.currentRole,
    company: row.company,
    keyExperience: row.keyExperience,
    achievements: parseList(row.achievements),
    valueProposition: row.valueProposition,
    preferredNextStep: row.preferredNextStep,
    linkedinUrl: row.linkedinUrl,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export function createContactData(input: ContactCreateInput): Prisma.ContactCreateInput {
  const company = input.company ?? null;
  const industry = input.industry ?? null;
  const headline = input.headline ?? null;
  return {
    fullName: input.fullName,
    linkedinId: input.linkedinId,
    linkedinUrl: input.linkedinUrl ?? null,
    headline,
    occupation: input.occupation,
    company,
    industry,
    location: input.location ?? null,
    interests: dumpList(input.interests),
    notes: input.notes ?? null,
    status: input.status ?? "NEW",
    ...searchFields({
      fullName: input.fullName,
      linkedinId: input.linkedinId,
      headline,
      occupation: input.occupation,
      company,
      industry,
    }),
  };
}

export function patchContactData(current: Contact, input: ContactPatchInput): Prisma.ContactUpdateInput {
  const fullName = input.fullName ?? current.fullName;
  const linkedinId = input.linkedinId ?? current.linkedinId;
  const headline = input.headline === undefined ? current.headline : input.headline;
  const occupation = input.occupation ?? current.occupation;
  const company = input.company === undefined ? current.company : input.company;
  const industry = input.industry === undefined ? current.industry : input.industry;
  const interests = input.interests ?? parseList(current.interests);
  const status = input.status ?? current.status;
  return {
    fullName,
    linkedinId,
    linkedinUrl: input.linkedinUrl === undefined ? current.linkedinUrl : input.linkedinUrl,
    headline,
    occupation,
    company,
    industry,
    location: input.location === undefined ? current.location : input.location,
    interests: dumpList(interests),
    notes: input.notes === undefined ? current.notes : input.notes,
    status,
    ...(input.status === "SENT" && current.status !== "SENT" ? { lastContactedAt: new Date() } : {}),
    ...searchFields({ fullName, linkedinId, headline, occupation, company, industry }),
  };
}

function searchFields(input: {
  fullName: string;
  linkedinId: string;
  headline: string | null;
  occupation: string;
  company: string | null;
  industry: string | null;
}) {
  return {
    companyKey: fold(input.company ?? ""),
    industryKey: fold(input.industry ?? ""),
    searchText: fold(
      [input.fullName, input.company, input.headline, input.linkedinId, input.occupation].filter(Boolean).join(" "),
    ),
  };
}
