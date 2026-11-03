import { NextResponse } from "next/server";
import { importContactsCsv } from "@/lib/importContacts";
import { errorJson } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file");
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "Выберите CSV-файл" }, { status: 400 });
    }
    if (file.size > 15_000_000) {
      return NextResponse.json({ error: "Файл больше 15 МБ" }, { status: 400 });
    }
    const text = (await file.text()).replace(/^\uFEFF/, "").replace(/^sep=.\r?\n/i, "");
    const result = await importContactsCsv(text);
    if (result.created === 0 && result.updated === 0 && result.errors.length > 0) {
      return NextResponse.json({ error: result.errors[0], ...result }, { status: 400 });
    }
    return NextResponse.json(result);
  } catch (error) {
    return errorJson(error, 500);
  }
}
