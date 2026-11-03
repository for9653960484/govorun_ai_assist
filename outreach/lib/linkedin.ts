export function linkedinIdFromUrl(value: string): string {
  const trimmed = value.trim();
  if (!/^https?:\/\//i.test(trimmed)) return trimmed.replace(/^\/+|\/+$/g, "");
  try {
    const parts = new URL(trimmed).pathname.split("/").filter(Boolean);
    const profileIndex = parts.findIndex((part) => part.toLowerCase() === "in");
    const id = profileIndex >= 0 ? parts[profileIndex + 1] : parts[parts.length - 1];
    return decodeURIComponent(id ?? trimmed);
  } catch {
    return trimmed;
  }
}

export function nameFromLinkedinId(linkedinId: string): string {
  return linkedinId
    .split(/[-_.]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toLocaleUpperCase("ru") + part.slice(1))
    .join(" ");
}

export type LinkedInAccount = {
  url: string;
  name: string;
  linkedinId: string;
};

export function linkedInAccountFromEnv(): LinkedInAccount | null {
  const url = process.env.LINKEDIN_PROFILE_URL?.trim() ?? "";
  if (!url) return null;
  const linkedinId = linkedinIdFromUrl(url);
  if (!linkedinId) return null;
  const name = process.env.LINKEDIN_PROFILE_NAME?.trim() || nameFromLinkedinId(linkedinId);
  return { url, name, linkedinId };
}
