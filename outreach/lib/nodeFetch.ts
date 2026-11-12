import https from "node:https";
import type { IncomingHttpHeaders } from "node:http";

export function nodeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
  const headers = new Headers(init?.headers);
  const body = bodyBuffer(init?.body);
  if (body && !headers.has("content-length")) headers.set("content-length", String(body.length));

  return new Promise((resolve, reject) => {
    const request = https.request(
      url,
      { method: init?.method ?? "GET", headers: Object.fromEntries(headers) },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk: Buffer) => chunks.push(chunk));
        response.on("end", () => {
          resolve(
            new Response(Buffer.concat(chunks), {
              status: response.statusCode ?? 500,
              headers: flattenHeaders(response.headers),
            }),
          );
        });
      },
    );
    request.setTimeout(60_000, () => request.destroy(new Error("timeout")));
    const signal = init?.signal;
    if (signal) {
      if (signal.aborted) request.destroy(signal.reason instanceof Error ? signal.reason : new Error("aborted"));
      else signal.addEventListener("abort", () => request.destroy(signal.reason instanceof Error ? signal.reason : new Error("aborted")), { once: true });
    }
    request.on("error", reject);
    if (body) request.write(body);
    request.end();
  });
}

function bodyBuffer(body: BodyInit | null | undefined): Buffer | undefined {
  if (body == null) return undefined;
  if (typeof body === "string") return Buffer.from(body);
  if (body instanceof Uint8Array) return Buffer.from(body);
  throw new Error("Неподдерживаемое тело запроса к модели");
}

function flattenHeaders(headers: IncomingHttpHeaders): [string, string][] {
  return Object.entries(headers).flatMap(([key, value]) => {
    if (value === undefined) return [];
    return [[key, Array.isArray(value) ? value.join(", ") : value]];
  });
}
