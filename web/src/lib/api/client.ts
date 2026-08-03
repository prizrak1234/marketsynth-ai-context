import { getApiBaseUrl, getApiKey } from "@/lib/api/config";
import { ApiError, extractApiErrorInfo, parseErrorBody } from "@/lib/api/errors";

export { ApiError };
export type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

function buildHeaders(init?: HeadersInit, hasBody?: boolean): Headers {
  const headers = new Headers(init);
  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // Prefer cookie session (credentials: include). Optional Bearer only for
  // non-browser/service clients via env — never from localStorage (CPH.3).
  const apiKey = getApiKey();
  if (apiKey && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${apiKey}`);
  }
  return headers;
}

export async function apiFetch(
  path: string,
  options: ApiRequestOptions = {},
): Promise<Response> {
  const base = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path.startsWith("/") ? "" : "/"}${path}`;
  const hasBody = options.body !== undefined;
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers: buildHeaders(options.headers, hasBody),
    body: hasBody ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
    cache: "no-store",
    credentials: "include",
  });
  return response;
}

export async function apiJson<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    const body = await parseErrorBody(response);
    const { message, errorCode } = extractApiErrorInfo(body, response.status);
    throw new ApiError(message, response.status, body, errorCode);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
