export type CsvRow = Record<string, string>;

export function parseCsv(source: string): CsvRow[] {
  const text = source.replace(/^\uFEFF/, "");
  const delimiter = detectDelimiter(text);
  const table = parseTable(text, delimiter).filter((row) => row.some((cell) => cell.trim().length > 0));
  if (table.length === 0) return [];
  const headerAt = table.findIndex((row) =>
    row.some((cell) => /^(fullname|first name|linkedinid)$/i.test(cell.trim())),
  );
  const start = headerAt >= 0 ? headerAt : 0;
  const header = table[start].map((cell) => cell.trim());
  return table.slice(start + 1).map((row) => {
    const record: CsvRow = {};
    header.forEach((name, index) => {
      if (name) record[name] = (row[index] ?? "").trim();
    });
    return record;
  });
}

export function toCsv(headers: string[], rows: string[][]): string {
  const lines = [headers, ...rows].map((row) => row.map(escapeCell).join(","));
  return `\uFEFF${lines.join("\r\n")}`;
}

function detectDelimiter(text: string): "," | ";" {
  const line = text.split(/\r?\n/, 1)[0] ?? "";
  const commas = (line.match(/,/g) ?? []).length;
  const semicolons = (line.match(/;/g) ?? []).length;
  return semicolons > commas ? ";" : ",";
}

function parseTable(text: string, delimiter: "," | ";"): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          cell += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === delimiter) {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

function escapeCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}
