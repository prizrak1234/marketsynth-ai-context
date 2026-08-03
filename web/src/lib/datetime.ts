/** Default value for datetime-local: two hours ahead, top of hour (local). */
export function defaultFutureDatetimeLocal(): string {
  const date = new Date();
  date.setMinutes(0, 0, 0);
  date.setHours(date.getHours() + 2);
  return formatDatetimeLocalValue(date);
}

export function formatDatetimeLocalValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Converts datetime-local input (local timezone) to UTC ISO string for the API.
 */
export function localDatetimeInputToUtcIso(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error("Scheduled time is required");
  }
  const local = new Date(trimmed);
  if (Number.isNaN(local.getTime())) {
    throw new Error("Invalid scheduled time");
  }
  if (local.getTime() <= Date.now()) {
    throw new Error("Scheduled time must be in the future");
  }
  return local.toISOString();
}

/** Map API UTC ISO string to datetime-local input value (browser local TZ). */
/** Campaign dates: local input → UTC ISO, or null if empty (any time, not future-only). */
export function optionalLocalDatetimeToUtcIso(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const local = new Date(trimmed);
  if (Number.isNaN(local.getTime())) {
    throw new Error("Invalid datetime");
  }
  return local.toISOString();
}

export function assertEndAfterStart(
  startAt: string | null,
  endAt: string | null,
): void {
  if (startAt && endAt && new Date(endAt).getTime() <= new Date(startAt).getTime()) {
    throw new Error("end_at must be greater than start_at");
  }
}

export function utcIsoToDatetimeLocal(iso: string | null | undefined): string {
  if (!iso) {
    return defaultFutureDatetimeLocal();
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return defaultFutureDatetimeLocal();
  }
  return formatDatetimeLocalValue(date);
}

export function previewUtcFromLocalInput(value: string): string | null {
  try {
    if (!value.trim()) {
      return null;
    }
    const local = new Date(value);
    if (Number.isNaN(local.getTime())) {
      return null;
    }
    return local.toISOString();
  } catch {
    return null;
  }
}
