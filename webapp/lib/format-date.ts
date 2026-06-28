export function formatLocaleDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = Date.now();
  const diffSec = Math.round((date.getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  const absSec = Math.abs(diffSec);
  if (absSec < 60) {
    return rtf.format(diffSec, "second");
  }

  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) {
    return rtf.format(diffMin, "minute");
  }

  const diffHour = Math.round(diffMin / 60);
  if (Math.abs(diffHour) < 24) {
    return rtf.format(diffHour, "hour");
  }

  const diffDay = Math.round(diffHour / 24);
  if (Math.abs(diffDay) < 30) {
    return rtf.format(diffDay, "day");
  }

  const diffMonth = Math.round(diffDay / 30);
  if (Math.abs(diffMonth) < 12) {
    return rtf.format(diffMonth, "month");
  }

  const diffYear = Math.round(diffMonth / 12);
  return rtf.format(diffYear, "year");
}
