import i18n from "./index";

function bcp47(): string {
  return i18n.language === "ar" ? "ar" : "en";
}

export function formatNumber(value: number | string | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return String(value);
  return new Intl.NumberFormat(bcp47(), {
    useGrouping: true,
    maximumFractionDigits: 2,
    ...opts,
    numberingSystem: "latn",
  } as Intl.NumberFormatOptions).format(n);
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(bcp47(), {
    year: "numeric",
    month: "short",
    day: "2-digit",
    numberingSystem: "latn",
  } as Intl.DateTimeFormatOptions).format(d);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(bcp47(), {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    numberingSystem: "latn",
  } as Intl.DateTimeFormatOptions).format(d);
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  const kb = bytes / 1024;
  return `${formatNumber(Math.round(kb))} KB`;
}
