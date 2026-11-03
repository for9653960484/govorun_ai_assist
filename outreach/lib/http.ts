import { NextResponse } from "next/server";
import { ZodError } from "zod";

export function errorJson(error: unknown, status = 400) {
  if (error instanceof ZodError) {
    const message = error.issues.map((issue) => issue.message).join("; ");
    return NextResponse.json({ error: message || "Проверьте заполненные поля" }, { status: 400 });
  }
  if (isUniqueViolation(error)) {
    return NextResponse.json({ error: "Контакт с таким LinkedIn ID уже есть" }, { status: 409 });
  }
  if (error instanceof Error && !("code" in error)) {
    return NextResponse.json({ error: error.message || "Не удалось выполнить запрос" }, { status });
  }
  return NextResponse.json({ error: "Не удалось выполнить запрос" }, { status: 500 });
}

export function isUniqueViolation(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "P2002";
}
