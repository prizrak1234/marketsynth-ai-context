export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;
  readonly errorCode: string | null;

  constructor(message: string, status: number, body: unknown, errorCode: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.errorCode = errorCode;
  }
}

export function extractApiErrorInfo(
  body: unknown,
  status: number,
): { message: string; errorCode: string | null } {
  if (typeof body === "object" && body !== null) {
    const record = body as Record<string, unknown>;
    const errorCode =
      typeof record.error_code === "string"
        ? record.error_code
        : typeof record.detail === "string"
          ? record.detail
          : null;
    const safeMessage =
      typeof record.safe_message === "string" && record.safe_message.trim()
        ? record.safe_message.trim()
        : null;
    if (safeMessage) {
      return { message: safeMessage, errorCode };
    }
    if (errorCode && errorCode !== "Not Found") {
      // Domain code only — presentation layer must map via commercial-error-mapper.
      return { message: "", errorCode };
    }
  }
  if (status === 404) {
    return { message: "not_found", errorCode: "not_found" };
  }
  return { message: `Request failed (${status})`, errorCode: null };
}

export async function parseErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  try {
    return await response.text();
  } catch {
    return null;
  }
}
