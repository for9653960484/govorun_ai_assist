export function fold(value: string): string {
  return value.trim().toLocaleLowerCase("ru").replaceAll("ё", "е");
}

export function parseList(value: string | null | undefined): string[] {
  if (!value) return [];
  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  } catch {
    return [];
  }
}

export function dumpList(values: string[]): string {
  return JSON.stringify(values.map((item) => item.trim()).filter(Boolean));
}

export function linesToList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function listToLines(values: string[]): string {
  return values.join("\n");
}

export function splitMulti(value: string): string[] {
  const trimmed = value.trim();
  if (!trimmed) return [];
  const delimiter = trimmed.includes("|") ? "|" : trimmed.includes("\n") ? "\n" : trimmed.includes(";") ? ";" : null;
  if (!delimiter) return [trimmed];
  return trimmed
    .split(delimiter)
    .map((item) => item.trim())
    .filter(Boolean);
}
