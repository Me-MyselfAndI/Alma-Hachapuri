const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const relativeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
});

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffSeconds = Math.round((then - now) / 1000);
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 60) {
    return relativeFormatter.format(diffSeconds, "second");
  }

  const diffMinutes = Math.round(diffSeconds / 60);
  if (Math.abs(diffMinutes) < 60) {
    return relativeFormatter.format(diffMinutes, "minute");
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return relativeFormatter.format(diffHours, "hour");
  }

  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 30) {
    return relativeFormatter.format(diffDays, "day");
  }

  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 12) {
    return relativeFormatter.format(diffMonths, "month");
  }

  const diffYears = Math.round(diffMonths / 12);
  return relativeFormatter.format(diffYears, "year");
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
