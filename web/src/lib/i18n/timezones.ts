/** IANA timezone list for Settings — prefer browser API, with a stable fallback. */

export type TimezoneGroup = {
  region: string;
  zones: string[];
};

const FALLBACK_ZONES: string[] = [
  "UTC",
  "Europe/Moscow",
  "Europe/Berlin",
  "Europe/London",
  "Europe/Paris",
  "Europe/Madrid",
  "Europe/Rome",
  "Europe/Istanbul",
  "Asia/Baku",
  "Asia/Dubai",
  "Asia/Tashkent",
  "Asia/Almaty",
  "Asia/Bishkek",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Singapore",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Australia/Sydney",
  "Australia/Melbourne",
];

function listSupportedTimeZones(): string[] {
  try {
    const intl = Intl as typeof Intl & {
      supportedValuesOf?: (key: string) => string[];
    };
    if (typeof intl.supportedValuesOf === "function") {
      const zones = intl.supportedValuesOf("timeZone");
      if (Array.isArray(zones) && zones.length > 0) {
        return ["UTC", ...zones.filter((z) => z !== "UTC")];
      }
    }
  } catch {
    /* older engines */
  }
  return FALLBACK_ZONES;
}

function regionOf(zone: string): string {
  if (zone === "UTC" || zone === "GMT") return "UTC";
  const slash = zone.indexOf("/");
  if (slash === -1) return "Other";
  return zone.slice(0, slash);
}

/** Grouped IANA zones for the timezone <select>. */
export function getTimezoneGroups(): TimezoneGroup[] {
  const zones = listSupportedTimeZones();
  const byRegion = new Map<string, string[]>();
  for (const zone of zones) {
    const region = regionOf(zone);
    const list = byRegion.get(region) ?? [];
    list.push(zone);
    byRegion.set(region, list);
  }

  const preferredOrder = [
    "UTC",
    "Europe",
    "Asia",
    "America",
    "Australia",
    "Africa",
    "Pacific",
    "Atlantic",
    "Indian",
    "Antarctica",
    "Other",
  ];

  const groups: TimezoneGroup[] = [];
  for (const region of preferredOrder) {
    const list = byRegion.get(region);
    if (!list?.length) continue;
    list.sort((a, b) => a.localeCompare(b));
    groups.push({ region, zones: list });
    byRegion.delete(region);
  }
  for (const [region, list] of [...byRegion.entries()].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    list.sort((a, b) => a.localeCompare(b));
    groups.push({ region, zones: list });
  }
  return groups;
}
